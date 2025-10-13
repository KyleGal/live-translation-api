#!/usr/bin/env python3
"""
Advanced test architecture for live transcription with accurate speaker diarization.

This script combines:
1. Live transcription to console (like test_stream.py)
2. Full audio recording during session
3. Post-session diarization with word-level speaker alignment
4. VAD-based boundary refinement with ±0.5s overlap handling

Usage:
    python test_architecture.py [options]

    Press 'q' + Enter or Ctrl+C to stop and process diarization

Architecture:
    - During session: Captures audio, shows live transcription
    - After session: Runs full Whisper with word timestamps + pyannote diarization
    - Aligns words to speakers based on timing overlap
    - Outputs speaker-attributed transcript
"""
import requests
import numpy as np
import pyaudio
import webrtcvad
import whisper
from queue import Queue
import time
from datetime import datetime, timedelta
import json
import os
import wave
import argparse
from dataclasses import dataclass
from typing import List, Optional, Dict
from dotenv import load_dotenv
import warnings
import speech_recognition as sr
import noisereduce as nr
import soundfile as sf

# Load environment variables
load_dotenv()
warnings.filterwarnings('ignore')

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

# Diarization parameters
OVERLAP_MARGIN = 0.5  # ±0.5s overlap for boundary refinement


@dataclass
class Word:
    """Represents a word with timing and speaker information"""
    text: str
    start: float
    end: float
    speaker: Optional[str] = None
    probability: float = 1.0


@dataclass
class SpeakerSegment:
    """Represents a speaker segment from diarization"""
    speaker_id: str
    start: float
    end: float


@dataclass
class Turn:
    """Represents a speaker turn with transcribed text"""
    speaker: str
    start: float
    end: float
    text: str
    words: List[Word]


class LiveDiarizationStreamer:
    """
    Combines live transcription with post-session accurate diarization
    """

    def __init__(self, api_base_url: str):
        # Extract base URL for API routes
        if '/transcription' in api_base_url:
            self.api_base_url = api_base_url.replace('/transcription', '')
        else:
            self.api_base_url = api_base_url

        self.transcription_url = f"{self.api_base_url}/transcription"
        self.diarization_url = f"{self.api_base_url}/diarization"

        self.audio = pyaudio.PyAudio()
        self.vad = webrtcvad.Vad(VAD_MODE)
        self.is_running = False

        # Audio buffering
        self.audio_queue = Queue()
        self.phrase_bytes = bytes()
        self.phrase_time = None

        # timeout
        self.record_timeout = 2
        self.phrase_timeout = 3

        # Audio recording storage
        self.all_audio_frames = []

    def start(self):
        """Start audio capture and live transcription"""
        self.is_running = True

        audio_model = whisper.load_model("base")

        recorder = sr.Recognizer()
        recorder.energy_threshold = 1000
        recorder.dynamic_energy_threshold = False


        transcription = ['']
        source = sr.Microphone(sample_rate=16000)
        with source:
            recorder.adjust_for_ambient_noise(source)

        stop_listening = recorder.listen_in_background(source, self.record_callback, phrase_time_limit=self.record_timeout)

        print("Model loaded.\n")

        while True:
            try:
                now = datetime.now()
                # Pull raw recorded audio from the queue.
                if not self.audio_queue.empty():
                    print("processing")
                    phrase_complete = False
                    # If enough time has passed between recordings, consider the phrase complete.
                    # Clear the current working audio buffer to start over with the new data.
                    if self.phrase_time and now - self.phrase_time > timedelta(seconds=self.phrase_timeout):
                        self.phrase_bytes = bytes()
                        phrase_complete = True
                    # This is the last time we received new audio data from the queue.
                    self.phrase_time = now
                    
                    # Combine audio data from queue
                    audio_data = b''.join(self.audio_queue.queue)
                    self.audio_queue.queue.clear()

                    # Add the new audio data to the accumulated data for this phrase
                    self.phrase_bytes += audio_data

                    # Convert in-ram buffer to something the model can use directly without needing a temp file.
                    # Convert data from 16 bit wide integers to floating point with a width of 32 bits.
                    # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
                    audio_np = np.frombuffer(self.phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                    # Read the transcription.
                    result = audio_model.transcribe(audio_np, fp16=False)
                    text = result['text'].strip()

                    # If we detected a pause between recordings, add a new item to our transcription.
                    # Otherwise edit the existing one.
                    if phrase_complete:
                        transcription.append(text)
                    else:
                        transcription[-1] = text

                    # Clear the console to reprint the updated transcription.
                    os.system('cls' if os.name=='nt' else 'clear')
                    for line in transcription:
                        print(line)
                    # Flush stdout.
                    print('', end='', flush=True)
                else:
                    # Infinite loops are bad for processors, must sleep.
                    time.sleep(0.25)
            except KeyboardInterrupt:
                print("\nStopping...")
                break
            # finally:
            #     if self.is_running:
            #         self.stop() 

        print("\n\nMono Transcription:")
        for line in transcription:
            print(line)

        if self.is_running:
            stop_listening(wait_for_stop=False)
            print("Stopped listening.")
            self.stop()

    def record_callback(self, _, audio:sr.AudioData) -> None:
        """Callback for audio stream - processes each chunk"""
        data = audio.get_raw_data()

        # Store all audio frames for later processing
        self.all_audio_frames.append(data)

        # Queue for transcription processing
        self.audio_queue.put(data)

    def clean_up_audio(self, audio_data):
        """Clean up audio after recording for better diarization and translation"""

        # temp audio file that we can process
        temp_filename = "temp_file.wav"
        with wave.open(temp_filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.audio.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data)

        # Noise Reduction
        temp_denoised = "temp_denoised.wav"

        y, sr = sf.read(temp_filename)
        reduced = nr.reduce_noise(y=y, sr=sr, prop_decrease=0.8)  # 0.6–0.9 typical
        sf.write(temp_denoised, reduced, sr)

        # Dereverberation

        # Normalization

        with wave.open(temp_denoised, 'rb') as wf:
            # n_channels = wf.getnchannels()
            # sampwidth = wf.getsampwidth()
            # framerate = wf.getframerate()
            n_frames = wf.getnframes()

            audio_bytes = wf.readframes(n_frames)

        # Convert to float32 NumPy array normalized between -1 and 1
        audio_data = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

        os.remove(temp_filename)
        os.remove(temp_denoised)
        return audio_data


    def save_audio(self) -> Optional[str]:
        """Save recorded audio to WAV file and return filename"""
        if not self.all_audio_frames:
            print("\nNo audio recorded to save.")
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"recording_{timestamp}.wav"

        try:
            audio_data = b''.join(self.all_audio_frames)

            # raw audio
            with wave.open("raw_"+filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(FORMAT))
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_data)
            
            # post-hoc preprocessed audio
            processed_audio_data = self.clean_up_audio(audio_data)

            processed_filename = "processed_"+filename
            with wave.open(processed_filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(FORMAT))
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(processed_audio_data)

            return processed_filename
        except Exception as e:
            print(f"\n❌ Error saving audio: {e}")
            return None

    def transcribe_audio(self, audio_path: str):
        """Transcribe audio file with word-level timestamps"""
        print("\n🎙️  Running transcription with word timestamps...")

        response = requests.post(
            self.transcription_url,
            json={'audio_path': audio_path},
            headers={'Content-Type': 'application/json'},
            timeout=600
        )

        if response.status_code != 200:
            raise ValueError(f"Transcription failed: {response.status_code}")

        result = response.json()
        transcription = result['data']['transcription']
        timestamps = result['data']['timestamps']

        print(f"✅ Transcribed: \"{transcription[:100]}...\"")
        print(f"✅ Got {len(timestamps)} word chunks")

        return transcription, timestamps

    def diarize_audio(self, audio_path: str) -> List[SpeakerSegment]:
        """Run speaker diarization on audio file"""
        print("\n📊 Running speaker diarization...")

        response = requests.post(
            self.diarization_url,
            json={'audio_path': audio_path},
            headers={'Content-Type': 'application/json'},
            timeout=600
        )

        if response.status_code != 200:
            raise ValueError(f"Diarization failed: {response.status_code}")

        result = response.json()
        speakers_data = result if isinstance(result, list) else result['data']['speakers']

        segments = [
            SpeakerSegment(
                speaker_id=seg['speaker_id'],
                start=float(seg['start']),
                end=float(seg['end'])
            )
            for seg in speakers_data
        ]

        num_speakers = len(set(s.speaker_id for s in segments))
        print(f"✅ Detected {len(segments)} segments from {num_speakers} speaker(s)")
        return segments

    def get_last_segment(self, diarization_segments):
        last_segment = None
        for segment in diarization_segments:
            last_segment = segment
        return last_segment

    def find_best_match(self, diarization_segments, start_time, end_time):
        best_match = None
        max_intersection = 0

        for segment in diarization_segments:
            turn_start = segment.start
            turn_end = segment.end

            # Calculate intersection manually
            intersection_start = max(start_time, turn_start)
            intersection_end = min(end_time, turn_end)

            if intersection_start < intersection_end:
                intersection_length = intersection_end - intersection_start
                if intersection_length > max_intersection:
                    max_intersection = intersection_length
                    best_match = (turn_start, turn_end, segment.speaker_id)

        return best_match

    def merge_consecutive_segments(self, segments):
        merged_segments = []
        previous_segment = None

        for segment in segments:
            if previous_segment is None:
                previous_segment = segment
            else:
                if segment[0] == previous_segment[0]:
                    # Merge segments of the same speaker that are consecutive
                    previous_segment = (
                        previous_segment[0],
                        previous_segment[1],
                        segment[2],
                        previous_segment[3] + segment[3]
                    )
                else:
                    merged_segments.append(previous_segment)
                    previous_segment = segment

        if previous_segment:
            merged_segments.append(previous_segment)

        return merged_segments

    def process_diarization(self, audio_file: str) -> List[Turn]:
        """Full diarization pipeline: transcribe + diarize + align + refine"""
        print("\n" + "=" * 80)
        print("POST-SESSION SPEAKER DIARIZATION")
        print("=" * 80)

        segments = self.diarize_audio(audio_file)
        transcription, timestamps = self.transcribe_audio(audio_file)
        # refined_segments = self.refine_boundaries_with_vad(audio_file, segments)
        # assigned_words = self.assign_words_to_speakers(words, refined_segments)
        # turns = self.create_speaker_turns(assigned_words)

        # return turns

        last_segment = self.get_last_segment(segments)

        speaker_transcriptions = []
        for chunk in timestamps:
            chunk_start = chunk['timestamp'][0]
            chunk_end = chunk['timestamp'][1]
            segment_text = chunk['text']

            # Handle the case where chunk_end is None
            if chunk_end is None:
                # Use the end of the last diarization segment as the default end time
                chunk_end = last_segment if last_segment is not None else chunk_start

            # Find the best matching speaker segment
            best_match = self.find_best_match(segments, chunk_start, chunk_end)
            if best_match:
                speaker = best_match[2]  # Extract the speaker label
                speaker_transcriptions.append((speaker, chunk_start, chunk_end, segment_text))
        
        # Merge consecutive segments of the same speaker
        speaker_transcriptions = self.merge_consecutive_segments(speaker_transcriptions)
        return speaker_transcriptions


    def stop(self):
        """Stop audio capture and run diarization"""
        self.is_running = False

        # Cleanup audio resources
        try:
            self.audio.terminate()
        except:
            pass

        os.system('cls' if os.name == 'nt' else 'clear')

        print("\n" + "=" * 80)
        print("SESSION ENDED - PROCESSING DIARIZATION")
        print("=" * 80)

        audio_file = self.save_audio()

        if not audio_file:
            return

        print(f"✅ Audio saved: {audio_file}")

        # Run diarization pipeline
        try:
            speaker_transcriptions = self.process_diarization(audio_file)
            for speaker in speaker_transcriptions:
                print(speaker)

            print("\n" + "=" * 80)
            print("✅ PROCESSING COMPLETE")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ Diarization error: {e}")
            import traceback
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description='Live transcription with post-session speaker diarization'
    )
    parser.add_argument(
        '--url',
        default='http://localhost:3000/api/translate',
        help='API base URL (default: http://localhost:3000/api/translate)'
    )

    args = parser.parse_args()

    streamer = LiveDiarizationStreamer(args.url)
    streamer.start()


if __name__ == "__main__":
    main()
