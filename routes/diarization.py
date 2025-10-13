"""
Diarization route - Speaker identification and segmentation
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import tempfile
import os
import warnings
import wave
import numpy as np
import torch
from pyannote.audio import Pipeline
from pyannote.audio.pipelines.utils.hook import ProgressHook
from dotenv import load_dotenv

# Suppress warnings
warnings.filterwarnings('ignore')

# Load environment variables
load_dotenv()

diarization_bp = Blueprint('diarization', __name__)


@diarization_bp.route('/diarization', methods=['POST'])
def diarize_audio():
    """
    POST /api/translate/diarization
    Speaker identification and segmentation

    Request:
    - Content-Type: application/octet-stream (raw audio bytes) OR
    - Content-Type: application/json with {"audio_path": "/path/to/file.wav"}
    - Headers:
      - X-Source-Language: Source language code (optional, default: auto-detect)
      - X-Sample-Rate: Sample rate in Hz (optional, default: 16000)
      - X-Min-Speakers: Minimum number of speakers (optional, default: 1)
      - X-Max-Speakers: Maximum number of speakers (optional, default: 10)

    Response:
    {
        "success": true,
        "data": {
            "speakers": [
                {
                    "speaker_id": "SPEAKER_00",
                    "start": 0.0,
                    "end": 5.2
                }
            ],
            "sourceLanguage": "en",
            "numSpeakers": 2,
            "timestamp": "2024-01-01T00:00:00.000000"
        }
    }
    """
    temp_audio_path = None
    cleanup_temp = False

    try:
        # Check if file path provided as JSON
        if request.content_type == 'application/json':
            json_data = request.get_json()
            audio_path = json_data.get('audio_path')

            if not audio_path or not os.path.exists(audio_path):
                return jsonify({
                    'success': False,
                    'error': 'Invalid audio path',
                    'message': 'audio_path must point to an existing file'
                }), 400

            temp_audio_path = audio_path
            cleanup_temp = False

            # Extract sample rate from WAV file
            with wave.open(audio_path, 'rb') as wf:
                sample_rate = wf.getframerate()
        else:
            # Get audio data from request body (raw bytes)
            audio_data = request.get_data()

            if not audio_data:
                return jsonify({
                    'success': False,
                    'error': 'No audio data provided'
                }), 400

            try:
                sample_rate = int(request.headers.get('X-Sample-Rate', '16000'))
                if sample_rate not in [8000, 16000, 22050, 44100, 48000]:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid sample rate',
                        'message': 'Sample rate must be one of: 8000, 16000, 22050, 44100, 48000'
                    }), 400
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid sample rate',
                    'message': 'X-Sample-Rate header must be a valid integer'
                }), 400

            # Convert raw audio bytes to numpy array and save to temp file
            audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            # Save audio to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
                temp_audio_path = temp_audio.name

            cleanup_temp = True

            # Write WAV file properly
            with wave.open(temp_audio_path, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                # Convert back to int16 for WAV
                audio_int16 = (audio_np * 32768.0).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())

        # Get preferences from headers
        source_language = request.headers.get('X-Source-Language', 'auto')

        try:
            min_speakers = int(request.headers.get('X-Min-Speakers', '1'))
            max_speakers = int(request.headers.get('X-Max-Speakers', '10'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid speaker parameters',
                'message': 'X-Min-Speakers and X-Max-Speakers must be valid integers'
            }), 400

        # Validate speaker parameters
        if min_speakers < 1 or max_speakers < min_speakers:
            return jsonify({
                'success': False,
                'error': 'Invalid speaker parameters. Min speakers must be >= 1 and max speakers must be >= min speakers'
            }), 400

        # Get HuggingFace token from environment
        HUGGINGFACE_ACCESS_TOKEN = os.getenv("HF_TOKEN")
        if not HUGGINGFACE_ACCESS_TOKEN:
            return jsonify({
                'success': False,
                'error': 'HuggingFace token not configured',
                'message': 'Please set HF_TOKEN environment variable'
            }), 500

        # Load diarization pipeline
        try:
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=HUGGINGFACE_ACCESS_TOKEN
            )
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Failed to load diarization pipeline',
                'message': str(e)
            }), 500

        # Send pipeline to GPU if available, otherwise use CPU
        pipeline.to(torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"))

        # Apply diarization pipeline
        try:
            print(f"Running diarization on {temp_audio_path}...")
            with ProgressHook() as hook:
                diarization = pipeline(temp_audio_path, hook=hook)
            print(f"Diarization complete. Type: {type(diarization)}")
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Diarization processing failed',
                'message': str(e)
            }), 500

        # Process diarization results
        diarized_speech = []

        for turn, speaker in diarization.speaker_diarization:
            diarized_speech.append({
                "speaker_id": speaker,
                "start": float(turn.start),
                "end": float(turn.end)
            })
            print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker_{speaker}")

        # Return properly formatted JSON response
        return jsonify({
            'success': True,
            'data': {
                'speakers': diarized_speech,
                'sourceLanguage': source_language,
                'numSpeakers': len(set(s['speaker_id'] for s in diarized_speech)),
                'timestamp': datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Transcription and diarization failed',
            'message': str(e)
        }), 500

    finally:
        # Clean up temporary file only if we created it
        if cleanup_temp and temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
