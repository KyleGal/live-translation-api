"""
Transcription route - Audio transcription with word-level timestamps
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import os

transcription_bp = Blueprint('transcription', __name__)

# Global Whisper transcriber - loaded once at startup
whisper_transcriber = None


class WhisperAudioTranscriber():
    def __init__(self, model_name="openai/whisper-large-v3-turbo"):
        # Configure the device for computation
        if torch.cuda.is_available():
            self.device = "cuda:0"
            self.torch_dtype = torch.float16
        elif torch.backends.mps.is_available():
            self.device = "mps"
            self.torch_dtype = torch.float16
        else:
            self.device = "cpu"
            self.torch_dtype = torch.float32

        # Load the model and processor
        try:
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_name,
                dtype=self.torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
            )
            self.model.to(self.device)

            self.processor = AutoProcessor.from_pretrained(model_name)

            # Configure the pipeline for automatic speech recognition
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                language="en",
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                dtype=self.torch_dtype,
                device=self.device,
                return_timestamps=True,
                generate_kwargs={"max_new_tokens": 400},
                chunk_length_s=5,
                stride_length_s=(1, 1),
            )
        except Exception as e:
            raise

    def transcribe(self, audio_path: str) -> tuple:
        try:
            # Perform transcription with timestamps
            result = self.pipe(audio_path)
            transcription = result['text']
            timestamps = result['chunks']
            return transcription, timestamps
        except Exception as e:
            return None, None


def init_whisper_model():
    """Initialize Whisper model at application startup"""
    global whisper_transcriber
    if whisper_transcriber is None:
        print("Loading Whisper model...")
        whisper_transcriber = WhisperAudioTranscriber()
        print("Model loaded")


@transcription_bp.route('/transcription', methods=['POST'])
def transcribe_audio():
    """
    POST /api/translate/transcription
    Transcribe audio file with word-level timestamps

    Request:
    - Content-Type: application/json with {"audio_path": "/path/to/file.wav"}

    Response:
    {
        "success": true,
        "data": {
            "transcription": "Full transcription text",
            "timestamps": [
                {
                    "text": "word or phrase",
                    "timestamp": [start_time, end_time]
                }
            ],
            "timestamp": "2024-01-01T00:00:00.000000"
        }
    }
    """
    global whisper_transcriber

    # Initialize model if not loaded
    if whisper_transcriber is None:
        init_whisper_model()

    try:
        # Get audio path from JSON
        if request.content_type != 'application/json':
            return jsonify({
                'success': False,
                'error': 'Invalid content type',
                'message': 'Content-Type must be application/json'
            }), 400

        json_data = request.get_json()
        audio_path = json_data.get('audio_path')

        if not audio_path or not os.path.exists(audio_path):
            return jsonify({
                'success': False,
                'error': 'Invalid audio path',
                'message': 'audio_path must point to an existing file'
            }), 400

        # Transcribe audio
        transcription, timestamps = whisper_transcriber.transcribe(audio_path)

        if transcription is None:
            return jsonify({
                'success': False,
                'error': 'Transcription failed',
                'message': 'Failed to transcribe audio'
            }), 500

        # Return result
        return jsonify({
            'success': True,
            'data': {
                'transcription': transcription,
                'timestamps': timestamps,
                'timestamp': datetime.now().isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Transcription failed',
            'message': str(e)
        }), 500
