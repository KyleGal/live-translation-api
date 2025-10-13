import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from routes.transcription import transcription_bp, init_whisper_model
from routes.diarization import diarization_bp

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)
CORS(app)

# Architecture Notes:
# - Simple stateless API for transcription and diarization
# - Models are loaded once at startup and shared across all requests (read-only)
# - Transcription: POST /api/translate/transcription with {"audio_path": "/path/to/file.wav"}
# - Diarization: POST /api/translate/diarization with {"audio_path": "/path/to/file.wav"}

# Initialize Whisper model at startup (shared, read-only)
print("Initializing Whisper model...")
with app.app_context():
    init_whisper_model()
print("Whisper initialization complete")

# Register blueprints
app.register_blueprint(transcription_bp, url_prefix='/api/translate')
app.register_blueprint(diarization_bp, url_prefix='/api/translate')

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check - returns server status
    """
    from datetime import datetime

    return {
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    port = int(os.getenv('PORT', 3000))
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode, use_reloader=False)
