from datetime import datetime
import tempfile
import os
import numpy as np
import whisper

from datetime import datetime, timedelta
from queue import Queue
import speech_recognition as sr
from time import sleep





# HARD CODED DEFAULTS #
# The last time a recording was retrieved from the queue.
phrase_time = None
# Thread safe Queue for passing data from the threaded recording callback.
data_queue = Queue()
# Bytes object which holds audio data for the current phrase
phrase_bytes = bytes()
# We use SpeechRecognizer to record our audio because it has a nice feature where it can detect when speech ends.
recorder = sr.Recognizer()
recorder.energy_threshold = 1000
# Definitely do this, dynamic energy compensation lowers the energy threshold dramatically to a point where the SpeechRecognizer never stops recording.
recorder.dynamic_energy_threshold = False

# load model
print("Loading Whisper model...")
whisper_model = whisper.load_model("turbo")
print("Whisper model loaded!")

# timeout times
record_timeout = 2
phrase_timeout = 3

transcription = ['']

print("Initializing microphone...")
source = sr.Microphone(sample_rate=16000)
with source:
    recorder.adjust_for_ambient_noise(source)
print("Microphone ready!")

def record_callback(_, audio:sr.AudioData) -> None:
    """
    Threaded callback function to receive audio data when recordings finish.
    audio: An AudioData containing the recorded bytes.
    """
    # Grab the raw bytes and push it into the thread safe queue.
    data = audio.get_raw_data()
    data_queue.put(data)
    print(f"[DEBUG] Audio captured: {len(data)} bytes", flush=True)

# Create a background thread that will pass us raw audio bytes.
# We could do this manually but SpeechRecognizer provides a nice helper.
recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)

# Cue the user that we're ready to go.
print("Model loaded.\n")
print("Listening... Speak into your microphone (Press Ctrl+C to stop)\n")

while True:
    try:
        now = datetime.now()
        # Pull raw recorded audio from the queue.
        if not data_queue.empty():
            # Combine all audio data from queue
            audio_chunks = []
            while not data_queue.empty():
                audio_chunks.append(data_queue.get())
            audio_data = b''.join(audio_chunks)

            # Check if we need to start a new phrase
            phrase_complete = False
            if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                # Process the accumulated phrase before starting new one
                if phrase_bytes:
                    # print(f"[DEBUG] Phrase complete, transcribing {len(phrase_bytes)} bytes", flush=True)
                    audio_np = np.frombuffer(phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                    result = whisper_model.transcribe(audio_np, fp16=False)
                    # print(result)
                    text = result['text'].strip()
                    # print(f"[DEBUG] Transcription: {text}", flush=True)
                    transcription.append(text)

                    # Clear the console to reprint the updated transcription.
                    os.system('cls' if os.name=='nt' else 'clear')
                    for line in transcription:
                        print(line)
                    print('', end='', flush=True)

                # Start new phrase
                phrase_bytes = audio_data
                phrase_complete = True
            else:
                # Add to current phrase
                phrase_bytes += audio_data

            # Update the last time we received audio
            phrase_time = now
            # print(f"[DEBUG] Accumulated {len(phrase_bytes)} bytes total", flush=True)
        else:
            # Infinite loops are bad for processors, must sleep.
            sleep(0.25)
    except KeyboardInterrupt:
        break

print("\n\nTranscription:")
for line in transcription:
    print(line)