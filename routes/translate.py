from flask import Blueprint, request, jsonify, Response
from datetime import datetime
import tempfile
import os
import numpy as np
import whisper
import json

from datetime import datetime, timedelta
from queue import Queue
import threading
from time import sleep

translate_bp = Blueprint('translate', __name__)
# Live translation is based on public domain implementation from https://github.com/davabase/whisper_real_time/tree/master.

# Global Whisper model - loaded once at startup
whisper_model = None

def init_whisper_model():
    """Initialize Whisper model at application startup"""
    global whisper_model
    if whisper_model is None:
        print("Loading Whisper model...")
        whisper_model = whisper.load_model("base")  # Using 'base' for faster loading
        print("Whisper model loaded successfully")

@translate_bp.route('/verbatim', methods=['POST'])
def translate_verbatim():
    """
    POST /api/translate/verbatim
    Streaming endpoint that transcribes audio bytes to verbatim text

    Request:
    - Content-Type: application/octet-stream (raw audio bytes stream - 16-bit PCM)
    - Headers:
      - X-Source-Language: Source language code (optional, default: auto-detect)
      - X-Target-Language: Target language code (optional, default: en)
      - X-Sample-Rate: Sample rate in Hz (optional, default: 16000)
      - X-Chunk-Size: Audio chunk size in bytes (optional, default: 8192)

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
    chunk_size = int(request.headers.get('X-Chunk-Size', '8192'))

    # Thread safe Queue for passing data from the stream reader
    data_queue = Queue()
    # Flag to signal when streaming is complete
    stream_complete = threading.Event()

    # Bytes object which holds audio data for the current phrase
    phrase_bytes = bytes()
    # The last time audio data was retrieved from the queue
    phrase_time = None
    # Timeout times
    phrase_timeout = 3

    def stream_reader():
        """
        Background thread that reads raw audio bytes from request stream
        and adds them to the data queue
        """
        try:
            while True:
                chunk = request.stream.read(chunk_size)
                if not chunk:
                    break
                data_queue.put(chunk)
            stream_complete.set()
        except Exception as e:
            print(f"Error reading stream: {e}")
            stream_complete.set()

    # Start background thread to read from request stream
    reader_thread = threading.Thread(target=stream_reader, daemon=True)
    reader_thread.start()

    def generate_transcriptions():
        """
        Generator function that yields transcription updates as SSE
        """
        nonlocal phrase_bytes, phrase_time

        transcription = ['']

        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Ready to transcribe'})}\n\n"

            while not stream_complete.is_set() or not data_queue.empty():
                now = datetime.now()

                if not data_queue.empty():
                    phrase_complete = False

                    # If enough time has passed, consider the phrase complete
                    if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                        phrase_bytes = bytes()
                        phrase_complete = True

                    phrase_time = now

                    # Get all available audio data from queue
                    audio_chunks = []
                    while not data_queue.empty():
                        try:
                            audio_chunks.append(data_queue.get_nowait())
                        except:
                            break

                    audio_data = b''.join(audio_chunks)
                    phrase_bytes += audio_data

                    # Only transcribe if we have enough data (at least 0.5 seconds of audio)
                    min_samples = int(sample_rate * 0.5)  # 0.5 seconds
                    if len(phrase_bytes) >= min_samples * 2:  # 2 bytes per sample (16-bit)
                        # Convert to numpy array
                        audio_np = np.frombuffer(phrase_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                        # Transcribe
                        result = whisper_model.transcribe(
                            audio_np,
                            language=None if source_language == 'auto' else source_language,
                            fp16=False
                        )
                        text = result['text'].strip()

                        if phrase_complete:
                            transcription.append(text)
                        else:
                            transcription[-1] = text

                        # Yield transcription update
                        yield f"data: {json.dumps({'type': 'transcription', 'text': text, 'is_final': phrase_complete, 'timestamp': now.isoformat()})}\n\n"
                else:
                    sleep(0.1)

            # Send final transcription
            final_text = ' '.join(transcription).strip()
            yield f"data: {json.dumps({'type': 'final', 'text': final_text, 'timestamp': datetime.now().isoformat()})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    # Return SSE stream
    return Response(generate_transcriptions(), mimetype='text/event-stream')


@translate_bp.route('/summary', methods=['POST'])
def translate_summary():
    """
    POST /api/translate/summary
    Transcribes, translates audio and provides a summary

    Request:
    - Content-Type: application/octet-stream (raw audio bytes)
    - Headers:
      - X-Source-Language: Source language code (optional, default: auto-detect)
      - X-Target-Language: Target language code (optional, default: en)
      - X-Summary-Length: short|medium|long (optional, default: medium)

    Response:
    {
        "success": true,
        "data": {
            "originalText": "Transcribed text in source language",
            "translatedText": "Translated text in target language",
            "summary": "Summarized version of translated text",
            "sourceLanguage": "en",
            "targetLanguage": "es",
            "summaryLength": "medium",
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
        target_language = request.headers.get('X-Target-Language', 'en')
        summary_length = request.headers.get('X-Summary-Length', 'medium')

        # Validate summary length
        if summary_length not in ['short', 'medium', 'long']:
            return jsonify({
                'success': False,
                'error': 'Invalid summary length. Must be: short, medium, or long'
            }), 400

        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name

        # TODO: Implement transcription logic using Whisper
        # Example: result = model.transcribe(temp_audio_path, fp16=False)
        # original_text = result["text"]
        original_text = "TODO: Implement Whisper transcription"

        # TODO: Implement translation logic
        # Example: translated_text = translator.translate(original_text, src=source_language, dest=target_language)
        translated_text = "TODO: Implement translation service"

        # TODO: Implement summarization logic
        # Example: summary = summarizer.summarize(translated_text, length=summary_length)
        summary = "TODO: Implement summarization service"

        return jsonify({
            'success': True,
            'data': {
                'originalText': original_text,
                'translatedText': translated_text,
                'summary': summary,
                'sourceLanguage': source_language,
                'targetLanguage': target_language,
                'summaryLength': summary_length,
                'timestamp': datetime.utcnow().isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Transcription and summarization failed',
            'message': str(e)
        }), 500

    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
