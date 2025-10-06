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

### 2. Verbatim Translation (Live Streaming)
```bash
POST /api/translate/verbatim
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
curl -X POST http://localhost:3000/api/translate/verbatim \
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

### 3. Summary Translation
```bash
POST /api/translate/summary
```

**Description:** Transcribes, translates, and summarizes audio.

**Request:**
- **Content-Type:** `application/octet-stream`
- **Headers:**
  - `X-Source-Language`: Source language code (optional, default: auto-detect)
  - `X-Target-Language`: Target language code (optional, default: en)
  - `X-Summary-Length`: `short` | `medium` | `long` (optional, default: medium)
- **Body:** Raw audio bytes

**Example:**
```bash
curl -X POST http://localhost:3000/api/translate/summary \
  -H "Content-Type: application/octet-stream" \
  -H "X-Source-Language: en" \
  -H "X-Target-Language: es" \
  -H "X-Summary-Length: medium" \
  --data-binary @audio.wav
```

**Response:**
```json
{
  "success": true,
  "data": {
    "originalText": "Full transcription text here...",
    "translatedText": "Full translated text here...",
    "summary": "Summarized version of the content",
    "sourceLanguage": "en",
    "targetLanguage": "es",
    "summaryLength": "medium",
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

✅ **Verbatim Endpoint (`/api/translate/verbatim`):**
- Real-time audio transcription using OpenAI Whisper (base model)
- Server-Sent Events (SSE) streaming
- Multi-threaded audio processing
- Phrase detection with 3-second timeout
- Supports custom sample rates and chunk sizes
- Language detection and source language specification

### Not Yet Implemented

❌ **Translation:** The verbatim endpoint currently only transcribes audio. Translation to target language is not implemented.

❌ **Summary Endpoint (`/api/translate/summary`):** Contains TODO placeholders for:
- Whisper transcription (lines 221-224 in routes/translate.py)
- Translation service (lines 226-228)
- Summarization logic (lines 230-232)

### Implementation Guide for Remaining Features

To complete the `/api/translate/summary` endpoint in `routes/translate.py`:

1. **Transcription (lines 221-224):**
   ```python
   # Use the global whisper_model
   result = whisper_model.transcribe(temp_audio_path, fp16=False)
   original_text = result["text"]
   ```

2. **Translation (lines 226-228):**
   ```python
   # Example using Google Translate:
   from googletrans import Translator
   translator = Translator()
   translated = translator.translate(original_text, src=source_language, dest=target_language)
   translated_text = translated.text
   ```

3. **Summarization (lines 230-232):**
   ```python
   # Example using transformers:
   from transformers import pipeline
   summarizer = pipeline("summarization")
   summary = summarizer(translated_text, max_length=130, min_length=30)[0]['summary_text']
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

1. ✅ ~~Implement Whisper transcription~~ (Completed for `/api/translate/verbatim`)
2. Add translation service to verbatim endpoint (Google Translate, DeepL, etc.)
3. Complete the `/api/translate/summary` endpoint implementation
4. Add summarization logic for summary endpoint
5. Add authentication/API keys for production
6. Implement rate limiting
7. Add request logging and monitoring
8. Test with various audio formats and sample rates

---

## License

[Specify your license here]
