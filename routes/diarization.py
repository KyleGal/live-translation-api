"""
Diarization route - Speaker identification and segmentation
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import tempfile
import os
import warnings
import torch
import torchvision
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
    Transcribes audio and identifies different speakers (speaker diarization)

    Request:
    - Content-Type: application/octet-stream (raw audio bytes)
    - Headers:
      - X-Source-Language: Source language code (optional, default: auto-detect)
      - X-Sample-Rate: Sample rate in Hz (optional, default: 16000)
      - X-Min-Speakers: Minimum number of speakers (optional, default: 1)
      - X-Max-Speakers: Maximum number of speakers (optional, default: 10)

    Response:
    {
        "success": true,
        "data": {
            "transcription": "Full transcription text",
            "speakers": [
                {
                    "speaker_id": "SPEAKER_00",
                    "text": "Speaker 00's text",
                    "start": 0.0,
                    "end": 5.2
                },
                {
                    "speaker_id": "SPEAKER_01",
                    "text": "Speaker 01's text",
                    "start": 5.5,
                    "end": 12.3
                }
            ],
            "sourceLanguage": "en",
            "numSpeakers": 2,
            "timestamp": "2024-01-01T00:00:00.000000"
        }
    }
    """
    temp_audio_path = None

    try:
        # Get audio data from request body
        audio_data = request.get_data()

        if not audio_data:
            return jsonify({
                'success': False,
                'error': 'No audio data provided'
            }), 400

        # Get preferences from headers
        source_language = request.headers.get('X-Source-Language', 'auto')
        sample_rate = int(request.headers.get('X-Sample-Rate', '16000'))
        min_speakers = int(request.headers.get('X-Min-Speakers', '1'))
        max_speakers = int(request.headers.get('X-Max-Speakers', '10'))

        # Validate speaker parameters
        if min_speakers < 1 or max_speakers < min_speakers:
            return jsonify({
                'success': False,
                'error': 'Invalid speaker parameters. Min speakers must be >= 1 and max speakers must be >= min speakers'
            }), 400

        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name

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
                use_auth_token=HUGGINGFACE_ACCESS_TOKEN
            )
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Failed to load diarization pipeline',
                'message': str(e)
            }), 500

        # Send pipeline to GPU if available, otherwise use CPU
        try:
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            pipeline.to(device)
            print(f"Using device: {device}")
        except Exception as e:
            print(f"Warning: Could not move pipeline to device: {e}")

        # Apply diarization pipeline
        try:
            with ProgressHook() as hook:
                diarization = pipeline(temp_audio_path, hook=hook)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Diarization processing failed',
                'message': str(e)
            }), 500

        # Process diarization results
        diarized_speech = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
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
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
