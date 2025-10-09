"""
Transcription route - Live audio transcription with streaming updates
"""
from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import numpy as np
import whisper
import json

transcription_bp = Blueprint('transcription', __name__)

# Global Whisper model - loaded once at startup
whisper_model = None


def init_whisper_model():
    """Initialize Whisper model at application startup"""
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model...")
        whisper_model = whisper.load_model("base")  # Using 'base' for faster loading
        print("Whisper model loaded successfully")


@transcription_bp.route('/transcription', methods=['POST'])
def transcribe_audio():
    """
    POST /api/translate/transcription
    Streaming endpoint that transcribes audio bytes to verbatim text

    Request:
    - Content-Type: application/octet-stream (raw audio bytes - 16-bit PCM)
    - Headers:
      - X-Source-Language: Source language code (optional, default: auto-detect)
      - X-Target-Language: Target language code (optional, default: en)
      - X-Sample-Rate: Sample rate in Hz (optional, default: 16000)

    Response:
    Server-Sent Events (SSE) stream with JSON objects:
    {
        "type": "transcription",
        "text": "Transcribed text",
        "is_final": false,
        "timestamp": "2024-01-01T00:00:00.000000"
    }
    """
    global whisper_model

    # Initialize model if not already loaded
    if whisper_model is None:
        init_whisper_model()

    # Get preferences from headers
    source_language = request.headers.get('X-Source-Language', 'auto')
    target_language = request.headers.get('X-Target-Language', 'en')
    sample_rate = int(request.headers.get('X-Sample-Rate', '16000'))

    # Read all audio data from request body
    try:
        audio_data = request.get_data()

        if not audio_data:
            return jsonify({
                'success': False,
                'error': 'No audio data provided'
            }), 400

        def generate_transcriptions():
            """
            Generator function that yields transcription updates as SSE
            """
            try:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Ready to transcribe'})}\n\n"

                # Only transcribe if we have enough data (at least 0.5 seconds of audio)
                min_samples = int(sample_rate * 0.5)  # 0.5 seconds
                if len(audio_data) >= min_samples * 2:  # 2 bytes per sample (16-bit)
                    # Convert to numpy array
                    audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                    # Transcribe
                    result = whisper_model.transcribe(
                        audio_np,
                        language=None if source_language == 'auto' else source_language,
                        fp16=False
                    )
                    text = result['text'].strip()

                    # Yield transcription update
                    now = datetime.now()
                    yield f"data: {json.dumps({'type': 'transcription', 'text': text, 'is_final': True, 'timestamp': now.isoformat()})}\n\n"

                    # Send final transcription
                    yield f"data: {json.dumps({'type': 'final', 'text': text, 'timestamp': datetime.now().isoformat()})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Audio too short'})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        # Return SSE stream
        return Response(generate_transcriptions(), mimetype='text/event-stream')

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Failed to process audio',
            'message': str(e)
        }), 500
