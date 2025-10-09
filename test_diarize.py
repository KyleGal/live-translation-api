#!/usr/bin/env python3
"""
Test client for speaker diarization with transcription
Sends audio file to /diarization and /transcription endpoints,
then merges the results to create speaker-attributed transcripts
"""
import requests
import sys
import json
import os
from dataclasses import dataclass
from typing import List, Optional
from pydub import AudioSegment
import tempfile
import argparse


# API Configuration
API_BASE_URL = "http://localhost:3000/api/translate"
DIARIZATION_ENDPOINT = f"{API_BASE_URL}/diarization"
TRANSCRIPTION_ENDPOINT = f"{API_BASE_URL}/transcription"


@dataclass
class Turn:
    """Represents a speaker turn with transcribed text"""
    speaker: str
    start: float
    end: float
    text: str


class AudioDiarizer:
    def __init__(self, audio_path: str, api_base_url: str = API_BASE_URL):
        self.audio_path = audio_path
        self.api_base_url = api_base_url
        self.diarization_url = f"{api_base_url}/diarization"
        self.transcription_url = f"{api_base_url}/transcription"

        # Validate audio file exists
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

    def load_audio(self) -> AudioSegment:
        """Load audio file using pydub"""
        print(f"Loading audio: {self.audio_path}")
        return AudioSegment.from_file(self.audio_path)

    def get_diarization(self, audio_data: bytes) -> List[dict]:
        """
        Send audio to diarization endpoint
        Returns list of speaker segments: [{"speaker_id": "SPEAKER_00", "start": 0.0, "end": 5.2}, ...]
        """
        print("\n📊 Running speaker diarization...")

        headers = {
            'Content-Type': 'application/octet-stream',
            'X-Source-Language': 'en',
            'X-Sample-Rate': '16000',
            'X-Min-Speakers': '1',
            'X-Max-Speakers': '10'
        }

        try:
            response = requests.post(
                self.diarization_url,
                data=audio_data,
                headers=headers,
                timeout=300  # 5 minutes for longer audio
            )

            if response.status_code == 200:
                result = response.json()

                # Handle the array response format from the current implementation
                if isinstance(result, list):
                    segments = result
                    print(f"✅ Detected {len(segments)} segments")
                    if segments:
                        num_speakers = len(set(s['speaker_id'] for s in segments))
                        print(f"✅ Identified {num_speakers} unique speaker(s)")
                    return segments
                # Handle the expected JSON format
                elif result.get('success'):
                    segments = result['data']['speakers']
                    print(f"✅ Detected {len(segments)} segments")
                    print(f"✅ Identified {result['data']['numSpeakers']} unique speaker(s)")
                    return segments
                else:
                    print(f"❌ Diarization failed: {result.get('error', 'Unknown error')}")
                    return []
            else:
                print(f"❌ Diarization request failed: {response.status_code}")
                print(f"Response: {response.text}")
                return []

        except requests.exceptions.Timeout:
            print("❌ Diarization request timed out")
            return []
        except Exception as e:
            print(f"❌ Error during diarization: {e}")
            return []

    def transcribe_segment(self, audio_segment: AudioSegment) -> str:
        """
        Transcribe a single audio segment using the transcription endpoint
        """
        # Convert segment to 16kHz mono WAV bytes
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)

        # Export to raw PCM bytes (16-bit)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp:
            audio_segment.export(tmp.name, format='wav')
            with open(tmp.name, 'rb') as f:
                # Skip WAV header (44 bytes) to get raw PCM data
                f.seek(44)
                audio_data = f.read()

        headers = {
            'Content-Type': 'application/octet-stream',
            'X-Source-Language': 'en',
            'X-Sample-Rate': '16000'
        }

        try:
            response = requests.post(
                self.transcription_url,
                data=audio_data,
                headers=headers,
                stream=True,
                timeout=60
            )

            # Parse SSE response
            text = ""
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        data = decoded[6:]  # Remove 'data: ' prefix
                        try:
                            json_data = json.loads(data)
                            if json_data['type'] == 'final':
                                text = json_data['text']
                                break
                        except json.JSONDecodeError:
                            pass

            return text.strip()

        except Exception as e:
            print(f"⚠️  Transcription error for segment: {e}")
            return ""

    def merge_diarization_with_transcription(self, segments: List[dict]) -> List[Turn]:
        """
        Transcribe each diarized segment and merge results
        """
        if not segments:
            print("No segments to transcribe")
            return []

        print(f"\n🎙️  Transcribing {len(segments)} speaker segments...")

        # Load audio
        audio = self.load_audio()

        turns: List[Turn] = []

        for i, seg in enumerate(segments, 1):
            speaker = seg['speaker_id']
            start = seg['start']
            end = seg['end']

            print(f"\r  [{i}/{len(segments)}] {speaker} ({start:.1f}s - {end:.1f}s)", end='', flush=True)

            # Extract audio slice (pydub works in milliseconds)
            audio_slice = audio[int(start * 1000):int(end * 1000)]

            # Transcribe
            text = self.transcribe_segment(audio_slice)

            if text:
                turns.append(Turn(
                    speaker=speaker,
                    start=start,
                    end=end,
                    text=text
                ))

        print("\n✅ Transcription complete!")
        return turns

    def process(self) -> List[Turn]:
        """
        Full pipeline: diarize, then transcribe each segment
        """
        # Load and prepare audio
        audio = self.load_audio()

        # Convert to 16kHz mono WAV for diarization
        audio_16k = audio.set_frame_rate(16000).set_channels(1)

        # Export to bytes
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as tmp:
            audio_16k.export(tmp.name, format='wav')
            with open(tmp.name, 'rb') as f:
                audio_data = f.read()

        # Get diarization
        segments = self.get_diarization(audio_data)

        if not segments:
            print("\n⚠️  No speaker segments detected. Cannot proceed with transcription.")
            return []

        # Transcribe each segment
        turns = self.merge_diarization_with_transcription(segments)

        return turns


def save_json(turns: List[Turn], output_path: str):
    """Save results as JSON"""
    data = [{"speaker": t.speaker, "start": t.start, "end": t.end, "text": t.text} for t in turns]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Saved JSON: {output_path}")


def save_txt(turns: List[Turn], output_path: str):
    """Save results as readable text transcript"""
    lines = []
    for t in turns:
        lines.append(f"[{t.start:6.2f}s - {t.end:6.2f}s] {t.speaker}:")
        lines.append(f"  {t.text}")
        lines.append("")  # blank line between turns

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"💾 Saved TXT: {output_path}")


def save_srt(turns: List[Turn], output_path: str):
    """Save results as SRT subtitle format"""
    lines = []
    for i, t in enumerate(turns, 1):
        # SRT format: index, timestamp, text
        start_time = format_srt_time(t.start)
        end_time = format_srt_time(t.end)

        lines.append(str(i))
        lines.append(f"{start_time} --> {end_time}")
        lines.append(f"{t.speaker}: {t.text}")
        lines.append("")  # blank line between entries

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"💾 Saved SRT: {output_path}")


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def print_summary(turns: List[Turn]):
    """Print a summary of the transcription"""
    print("\n" + "=" * 80)
    print("SPEAKER DIARIZATION & TRANSCRIPTION SUMMARY")
    print("=" * 80)

    if not turns:
        print("\nNo transcription available.")
        return

    # Count speakers
    speakers = set(t.speaker for t in turns)
    print(f"\nTotal speakers: {len(speakers)}")
    print(f"Total segments: {len(turns)}")

    # Show first few turns as preview
    print("\nPreview (first 5 segments):")
    print("-" * 80)
    for t in turns[:5]:
        print(f"\n[{t.start:6.2f}s - {t.end:6.2f}s] {t.speaker}:")
        print(f"  {t.text}")

    if len(turns) > 5:
        print(f"\n... ({len(turns) - 5} more segments)")

    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Diarize and transcribe audio file using the Live Translate API'
    )
    parser.add_argument(
        'audio_file',
        help='Path to audio file (supports .wav, .mp3, .m4a, .flac, etc.)'
    )
    parser.add_argument(
        '-o', '--output',
        default='transcript',
        help='Output file prefix (default: transcript)'
    )
    parser.add_argument(
        '--url',
        default=API_BASE_URL,
        help=f'API base URL (default: {API_BASE_URL})'
    )
    parser.add_argument(
        '--no-json',
        action='store_true',
        help='Skip JSON output'
    )
    parser.add_argument(
        '--no-txt',
        action='store_true',
        help='Skip TXT output'
    )
    parser.add_argument(
        '--srt',
        action='store_true',
        help='Generate SRT subtitle file'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("SPEAKER DIARIZATION & TRANSCRIPTION")
    print("=" * 80)
    print(f"\nInput file: {args.audio_file}")
    print(f"API URL: {args.url}")

    try:
        # Process audio
        diarizer = AudioDiarizer(args.audio_file, args.url)
        turns = diarizer.process()

        if not turns:
            print("\n⚠️  No results generated.")
            sys.exit(1)

        # Print summary
        print_summary(turns)

        # Save outputs
        if not args.no_json:
            save_json(turns, f"{args.output}.json")

        if not args.no_txt:
            save_txt(turns, f"{args.output}.txt")

        if args.srt:
            save_srt(turns, f"{args.output}.srt")

        print("\n✅ Processing complete!")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
