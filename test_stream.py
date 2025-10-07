#!/usr/bin/env python3
"""
Test client for streaming live audio to /verbatim endpoint
Captures audio from microphone, detects speech, and streams to server in real-time
with live transcription updates
"""
import requests
import numpy as np
import sys
import pyaudio
import webrtcvad
import threading
from collections import deque
from queue import Queue
import time
from datetime import datetime, timedelta
import json
import os
import select

# Audio recording parameters
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 30  # Duration of each audio chunk in milliseconds
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 480 samples for 30ms at 16kHz
FORMAT = pyaudio.paInt16
CHANNELS = 1

# Voice Activity Detection (VAD) parameters
VAD_MODE = 2  # Aggressiveness mode (0-3, 3 is most aggressive)
SILENCE_DURATION_MS = 2000  # Duration of silence before considering speech ended

# Live transcription parameters
TRANSCRIPTION_UPDATE_INTERVAL = 1.5  # Send updates every 1.5 seconds while speaking
MIN_AUDIO_LENGTH = 0.5  # Minimum audio length in seconds to transcribe

class AudioStreamer:
    def __init__(self, url):
        self.url = url
        self.audio = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad(VAD_MODE)
        self.stream = None
        self.is_running = False

        # Audio buffering
        self.audio_queue = Queue()  # Thread-safe queue for audio chunks
        self.phrase_bytes = bytes()  # Accumulated audio for current phrase
        self.phrase_time = None  # Last time we received audio
        self.last_transcription_time = None  # Last time we sent for transcription

        # State tracking
        self.is_speaking = False
        self.silence_frames = 0

        # Transcription history
        self.transcription_text = ""  # Full paragraph of all transcriptions
        self.current_transcription = ""  # Current segment being transcribed

    def start(self):
        """Start audio capture and streaming"""
        print("Starting live audio capture...")
        print(f"Sample rate: {SAMPLE_RATE} Hz")
        print(f"VAD mode: {VAD_MODE} (aggressiveness)")
        print(f"Live updates every: {TRANSCRIPTION_UPDATE_INTERVAL}s")
        print(f"Listening for speech... (Press 'q' + Enter or Ctrl+C to stop)\n")

        self.is_running = True

        # Open audio stream
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.audio_callback
        )

        self.stream.start_stream()

        # Start transcription processor thread
        processor_thread = threading.Thread(target=self.process_audio, daemon=True)
        processor_thread.start()

        # Start keyboard listener thread
        keyboard_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        keyboard_thread.start()

        try:
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nStopping...")
            self.stop()

    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for audio stream - processes each chunk"""
        if not self.is_running:
            return (None, pyaudio.paComplete)

        # Check if chunk contains speech using VAD
        is_speech = self.vad.is_speech(in_data, SAMPLE_RATE)

        if is_speech:
            if not self.is_speaking:
                self.is_speaking = True
                self.last_transcription_time = None

            # Add audio to queue
            self.audio_queue.put(in_data)
            self.silence_frames = 0
        else:
            if self.is_speaking:
                # Still buffer some silence after speech
                self.audio_queue.put(in_data)
                self.silence_frames += 1

                # If we've had enough silence, end the speech segment
                silence_chunks = SILENCE_DURATION_MS / CHUNK_DURATION_MS
                if self.silence_frames > silence_chunks:
                    self.is_speaking = False
                    # Signal end of phrase
                    self.audio_queue.put(None)

        return (in_data, pyaudio.paContinue)

    def process_audio(self):
        """Background thread that processes queued audio and sends for transcription"""
        while self.is_running:
            now = datetime.now()

            # Collect all available audio chunks from queue
            audio_chunks = []
            has_end_signal = False

            while not self.audio_queue.empty():
                chunk = self.audio_queue.get()
                if chunk is None:  # End of phrase signal
                    has_end_signal = True
                    break
                audio_chunks.append(chunk)

            if audio_chunks:
                # Add to phrase buffer
                audio_data = b''.join(audio_chunks)
                self.phrase_bytes += audio_data
                self.phrase_time = now

                # Check if we should send for transcription
                should_transcribe = False
                is_final = False

                if has_end_signal:
                    # End of speech - send final transcription
                    should_transcribe = True
                    is_final = True
                elif self.is_speaking:
                    # Check if enough time has passed for live update
                    if self.last_transcription_time is None:
                        should_transcribe = True
                    elif (now - self.last_transcription_time).total_seconds() >= TRANSCRIPTION_UPDATE_INTERVAL:
                        should_transcribe = True

                # Only transcribe if we have enough audio
                min_bytes = int(SAMPLE_RATE * MIN_AUDIO_LENGTH * 2)  # 2 bytes per sample
                if should_transcribe and len(self.phrase_bytes) >= min_bytes:
                    self.send_for_transcription(self.phrase_bytes, is_final)
                    self.last_transcription_time = now

                    if is_final:
                        # Clear phrase buffer for next speech segment
                        self.phrase_bytes = bytes()
                        self.phrase_time = None

            elif has_end_signal:
                # End signal but no audio (very short speech)
                if len(self.phrase_bytes) > 0:
                    self.send_for_transcription(self.phrase_bytes, is_final=True)
                self.phrase_bytes = bytes()
                self.phrase_time = None

            time.sleep(0.1)

    def send_for_transcription(self, audio_data, is_final=False):
        """Send audio data to server for transcription"""
        headers = {
            'Content-Type': 'application/octet-stream',
            'X-Source-Language': 'en',
            'X-Sample-Rate': str(SAMPLE_RATE),
        }

        try:
            marker = "[FINAL]" if is_final else "[LIVE]"

            response = requests.post(
                self.url,
                data=audio_data,
                headers=headers,
                stream=True,
                timeout=30
            )

            # Process SSE response
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        data = decoded[6:]  # Remove 'data: ' prefix

                        try:
                            json_data = json.loads(data)
                            if json_data['type'] == 'transcription':
                                text = json_data['text']
                                self.current_transcription = text

                                # Clear and redisplay full transcription
                                self.display_transcription(is_final)

                            elif json_data['type'] == 'final':
                                text = json_data['text']
                                if is_final and text:
                                    # Add to paragraph
                                    if self.transcription_text:
                                        self.transcription_text += " " + text
                                    else:
                                        self.transcription_text = text
                                    self.current_transcription = ""
                                    self.display_transcription(is_final=True)

                            elif json_data['type'] == 'error':
                                print(f"❌ Error: {json_data['message']}")

                        except json.JSONDecodeError:
                            pass

        except requests.exceptions.Timeout:
            print("⚠️  Server timeout")
        except Exception as e:
            print(f"❌ Error: {e}")

    def keyboard_listener(self):
        """Listen for keyboard input to stop transcription"""
        while self.is_running:
            try:
                # Check if stdin has data available (non-blocking)
                if sys.platform != 'win32':
                    # Unix-like systems
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == 'q':
                            print("\n'q' pressed, stopping transcription...")
                            self.is_running = False
                            break
                else:
                    # Windows - use simpler blocking approach
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8').lower()
                        if key == 'q':
                            print("\n'q' pressed, stopping transcription...")
                            self.is_running = False
                            break
            except:
                time.sleep(0.1)

    def display_transcription(self, is_final=False):
        """Display the current transcription state"""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

        print("=" * 80)
        print("LIVE TRANSCRIPTION")
        print("=" * 80)
        print()

        # Combine finalized text with current transcription for display
        full_text = self.transcription_text
        if self.current_transcription:
            if full_text:
                full_text += " " + self.current_transcription
            else:
                full_text = self.current_transcription

        # Display as paragraph with word wrap
        if full_text:
            # Simple word wrap at 80 characters
            words = full_text.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= 78:  # Leave room for padding
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            # Print the paragraph
            for line in lines:
                print(line)
        else:
            print("[No transcription yet]")

    def stop(self):
        """Stop audio capture"""
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

        # Print final summary
        print("\n" + "=" * 80)
        print("FINAL TRANSCRIPTION")
        print("=" * 80)
        print()

        if self.transcription_text:
            # Display final text as paragraph with word wrap
            words = self.transcription_text.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= 78:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

            for line in lines:
                print(line)
        else:
            print("[No transcription recorded]")

        print()
        print("=" * 80)
        print("\nAudio capture stopped.")

def main():
    url = "http://localhost:3000/api/translate/verbatim"

    streamer = AudioStreamer(url)
    streamer.start()

if __name__ == "__main__":
    main()
