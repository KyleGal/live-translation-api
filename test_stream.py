#!/usr/bin/env python3
"""
Test client for streaming audio to /verbatim endpoint
"""
import requests
import numpy as np
import sys

def generate_test_audio(duration=3, sample_rate=16000, frequency=440):
    """
    Generate a test audio signal (sine wave)

    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz

    Returns:
        bytes: Raw 16-bit PCM audio data
    """
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Generate sine wave
    audio = np.sin(frequency * 2 * np.pi * t)
    # Convert to 16-bit PCM
    audio_int16 = (audio * 32767).astype(np.int16)
    return audio_int16.tobytes()

def stream_audio_chunks(url, audio_data, chunk_size=8192):
    """
    Stream audio data in chunks to the endpoint

    Args:
        url: API endpoint URL
        audio_data: Raw audio bytes
        chunk_size: Size of each chunk to send
    """
    def generate():
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            yield chunk

    headers = {
        'Content-Type': 'application/octet-stream',
        'X-Source-Language': 'en',
        'X-Sample-Rate': '16000',
        'X-Chunk-Size': str(chunk_size)
    }

    print(f"Streaming {len(audio_data)} bytes to {url}...")
    print(f"Chunk size: {chunk_size} bytes\n")

    try:
        response = requests.post(
            url,
            data=generate(),
            headers=headers,
            stream=True
        )

        print("Receiving transcription stream:\n")

        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    data = decoded[6:]  # Remove 'data: ' prefix
                    print(f"Received: {data}")

        print("\nStream completed!")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def main():
    url = "http://localhost:3000/api/translate/verbatim"

    # Generate 3 seconds of test audio (silence/sine wave won't transcribe to meaningful text)
    print("Generating test audio...")
    audio_data = generate_test_audio(duration=3, sample_rate=16000)

    # Stream to endpoint
    stream_audio_chunks(url, audio_data, chunk_size=8192)

if __name__ == "__main__":
    main()
