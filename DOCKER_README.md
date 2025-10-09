# Live Translate API - Docker Setup

A dockerized Flask REST API for real-time audio transcription and translation.

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and start the container:**
   ```bash
   docker-compose up -d
   ```

2. **Check the health status:**
   ```bash
   curl http://localhost:3000/health
   ```

3. **Stop the container:**
   ```bash
   docker-compose down
   ```

### Using Docker CLI

1. **Build the image:**
   ```bash
   docker build -t live-translate-api .
   ```

2. **Run the container:**
   ```bash
   docker run -d -p 3000:3000 --name live-translate-api live-translate-api
   ```

3. **Stop the container:**
   ```bash
   docker stop live-translate-api
   docker rm live-translate-api
   ```

## API Endpoints

### 1. Health Check
```bash
GET /health
```

**Example:**
```bash
curl http://localhost:3000/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00.000000"
}
```

---

### 2. Live Transcription (Streaming)
```bash
POST /api/translate/transcription
```

**Description:** Real-time audio transcription using OpenAI Whisper. Returns Server-Sent Events (SSE) stream with live transcription updates.

**Request:**
- **Content-Type:** `application/octet-stream`
- **Headers:**
  - `X-Source-Language`: Source language code (optional, default: auto-detect)
  - `X-Target-Language`: Target language code (optional, default: en) - *Note: Translation not yet implemented*
  - `X-Sample-Rate`: Sample rate in Hz (optional, default: 16000)
  - `X-Chunk-Size`: Audio chunk size in bytes (optional, default: 8192)
- **Body:** Raw audio bytes stream (16-bit PCM)

**Example:**
```bash
curl -X POST http://localhost:3000/api/translate/transcription \
  -H "Content-Type: application/octet-stream" \
  -H "X-Source-Language: en" \
  -H "X-Sample-Rate: 16000" \
  --data-binary @audio.wav
```

**Response (Server-Sent Events):**
```
data: {"type": "status", "message": "Ready to transcribe"}

data: {"type": "transcription", "text": "Hello", "is_final": false, "timestamp": "2024-01-01T00:00:00.000000"}

data: {"type": "transcription", "text": "Hello, how are you?", "is_final": true, "timestamp": "2024-01-01T00:00:03.000000"}

data: {"type": "final", "text": "Hello, how are you?", "timestamp": "2024-01-01T00:00:05.000000"}
```

**Response Fields:**
- `type`: Event type (`status`, `transcription`, `final`, `error`)
- `text`: Transcribed text
- `is_final`: Whether this is a complete phrase (after 3 seconds of silence)
- `message`: Status or error message
- `timestamp`: ISO 8601 timestamp

---

### 3. Speaker Diarization
```bash
POST /api/translate/diarization
```

**Description:** Transcribes audio and identifies different speakers (speaker diarization).

**Request:**
- **Content-Type:** `application/octet-stream`
- **Headers:**
  - `X-Source-Language`: Source language code (optional, default: auto-detect)
  - `X-Sample-Rate`: Sample rate in Hz (optional, default: 16000)
  - `X-Min-Speakers`: Minimum number of speakers (optional, default: 1)
  - `X-Max-Speakers`: Maximum number of speakers (optional, default: 10)
- **Body:** Raw audio bytes

**Example:**
```bash
curl -X POST http://localhost:3000/api/translate/diarization \
  -H "Content-Type: application/octet-stream" \
  -H "X-Source-Language: en" \
  -H "X-Sample-Rate: 16000" \
  -H "X-Min-Speakers: 1" \
  -H "X-Max-Speakers: 5" \
  --data-binary @audio.wav
```

**Response:**
```json
{
  "success": true,
  "data": {
    "transcription": "Full transcription text here...",
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
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "success": false,
  "error": "Error type",
  "message": "Detailed error message"
}
```

**Common HTTP Status Codes:**
- `400` - Bad Request (missing audio data, invalid parameters)
- `500` - Internal Server Error (transcription/translation failed)

---

## Implementation Status

### Implemented Features

✅ **Transcription Endpoint (`/api/translate/transcription`):**
- Real-time audio transcription using OpenAI Whisper (base model)
- Server-Sent Events (SSE) streaming
- Multi-threaded audio processing
- Phrase detection with 3-second timeout
- Supports custom sample rates and chunk sizes
- Language detection and source language specification

### Not Yet Implemented

❌ **Translation:** The transcription endpoint currently only transcribes audio. Translation to target language is not implemented.

❌ **Diarization Endpoint (`/api/translate/diarization`):** Contains TODO placeholders for:
- Whisper transcription integration
- Speaker diarization logic (e.g., using pyannote.audio)
- Speaker segmentation and identification

### Implementation Guide for Remaining Features

To complete the `/api/translate/diarization` endpoint in `routes/translate.py`:

1. **Transcription:**
   ```python
   # Use the global whisper_model
   result = whisper_model.transcribe(temp_audio_path, fp16=False)
   transcription = result["text"]
   ```

2. **Speaker Diarization:**
   ```python
   # Example using pyannote.audio:
   from pyannote.audio import Pipeline
   diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
   diarization_result = diarization_pipeline(temp_audio_path)

   # Process diarization segments
   speakers = []
   for turn, _, speaker in diarization_result.itertracks(yield_label=True):
       speakers.append({
           "speaker_id": speaker,
           "text": "TODO: Align with transcription",
           "start": turn.start,
           "end": turn.end
       })
   ```

3. **Translation (for transcription endpoint):**
   ```python
   # Example using Google Translate:
   from googletrans import Translator
   translator = Translator()
   translated = translator.translate(transcription, src=source_language, dest=target_language)
   translated_text = translated.text
   ```

---

## Configuration

### Environment Variables

Create a `.env` file (optional):

```env
PORT=3000
```

### Supported Audio Formats

The API accepts raw audio bytes. Common formats include:
- WAV
- MP3
- M4A
- FLAC

FFmpeg is included in the Docker image to handle various audio formats.

---

## Development

### Running Locally (Without Docker)

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server:**
   ```bash
   python app.py
   ```

### Logs

View container logs:
```bash
docker-compose logs -f
```

Or for Docker CLI:
```bash
docker logs -f live-translate-api
```

---

## Troubleshooting

### Container won't start
- Check if port 3000 is already in use: `lsof -i :3000`
- View logs: `docker-compose logs`

### Audio processing fails
- Ensure FFmpeg is installed in the container (included in Dockerfile)
- Check audio file format compatibility
- Verify temporary file permissions

### Memory issues
- Whisper models can be memory-intensive
- The default model is `base` (74M params, ~1GB memory)
- Consider using a smaller model: `whisper.load_model("tiny")` (~39M params, ~300MB)
- Increase Docker memory limits if needed

### First run is slow
- Whisper downloads the model on first run (~140MB for base model)
- Model is cached in Docker volume `whisper-models`
- Subsequent runs will be faster

---

## Next Steps

1. ✅ ~~Implement Whisper transcription~~ (Completed for `/api/translate/transcription`)
2. Add translation service to transcription endpoint (Google Translate, DeepL, etc.)
3. Complete the `/api/translate/diarization` endpoint implementation
4. Add speaker diarization logic (e.g., using pyannote.audio)
5. Add authentication/API keys for production
6. Implement rate limiting
7. Add request logging and monitoring
8. Test with various audio formats and sample rates

---

## License

[Specify your license here]
