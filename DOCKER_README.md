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

### 2. Verbatim Translation
```bash
POST /api/translate/verbatim
```

**Description:** Transcribes and translates audio to verbatim text.

**Request:**
- **Content-Type:** `application/octet-stream`
- **Headers:**
  - `X-Source-Language`: Source language code (optional, default: auto-detect)
  - `X-Target-Language`: Target language code (optional, default: en)
- **Body:** Raw audio bytes

**Example:**
```bash
curl -X POST http://localhost:3000/api/translate/verbatim \
  -H "Content-Type: application/octet-stream" \
  -H "X-Source-Language: en" \
  -H "X-Target-Language: es" \
  --data-binary @audio.wav
```

**Response:**
```json
{
  "success": true,
  "data": {
    "originalText": "Hello, how are you?",
    "translatedText": "Hola, ¿cómo estás?",
    "sourceLanguage": "en",
    "targetLanguage": "es",
    "timestamp": "2024-01-01T00:00:00.000000"
  }
}
```

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

## Implementation Guide

The API routes have TODO placeholders for you to integrate your implementation logic:

### In `routes/translate.py`:

1. **Transcription (Lines 55-58, 144-147):**
   ```python
   # TODO: Implement transcription logic using Whisper
   # Example:
   import whisper
   model = whisper.load_model("base")
   result = model.transcribe(temp_audio_path, fp16=False)
   original_text = result["text"]
   ```

2. **Translation (Lines 60-62, 149-151):**
   ```python
   # TODO: Implement translation logic
   # Example using Google Translate:
   from googletrans import Translator
   translator = Translator()
   translated = translator.translate(original_text, src=source_language, dest=target_language)
   translated_text = translated.text
   ```

3. **Summarization (Lines 153-155):**
   ```python
   # TODO: Implement summarization logic
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
- Consider using a smaller model: `whisper.load_model("tiny")` or `"base"`
- Increase Docker memory limits if needed

---

## Next Steps

1. Implement Whisper transcription in `routes/translate.py`
2. Integrate translation service (Google Translate, DeepL, etc.)
3. Add summarization logic
4. Add authentication/API keys for production
5. Implement rate limiting
6. Add request logging and monitoring

---

## License

[Specify your license here]
