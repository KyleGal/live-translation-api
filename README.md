# Live Translate API

A real-time audio transcription and translation API built with Flask and OpenAI Whisper. This project enables live speech-to-text transcription with translation capabilities and summarization features.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Status](#project-status)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
  - [Running the Proof of Concept](#running-the-proof-of-concept)
  - [Running the Flask API](#running-the-flask-api)
  - [Testing](#testing)
- [API Reference](#api-reference)
- [Key Technologies](#key-technologies)
- [Project Structure](#project-structure)
- [Development Roadmap](#development-roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview

Live Translate API is a RESTful service designed to provide real-time audio transcription and translation capabilities. The project uses OpenAI's Whisper model for accurate speech recognition and supports WebSocket connections for live audio streaming.

**Current Focus:** Week 1 - Proof of Concept and foundational understanding of core technologies.

## Features

### Current (Proof of Concept)
- ✅ Real-time audio transcription via WebSocket
- ✅ Support for multiple audio formats (M4A, WAV, etc.)
- ✅ Base64 encoded audio transmission
- ✅ Automatic temporary file management
- ✅ CPU-compatible processing (FP32)

### Planned (Flask API Implementation)
- 🚧 RESTful API endpoints for transcription
- 🚧 Translation between languages
- 🚧 Text summarization capabilities
- 🚧 Configurable summary lengths (short, medium, long)
- 🚧 Multi-language support
- 🚧 Health check and monitoring endpoints

## Project Status

**Phase:** Proof of Concept ✅ | Initial Development 🚧

This project is currently in its first week of development, focusing on:
- Understanding OpenAI Whisper integration
- WebSocket communication patterns
- Audio processing workflows
- Flask REST API architecture planning

## Architecture

### Current: Proof of Concept WebSocket Server
```
Client (test_client.py)
    ↓ (WebSocket - Base64 audio)
WebSocket Server (proof-of-concept.py)
    ↓ (Temporary file)
Whisper Model (base)
    ↓ (Transcription)
Client (transcription text)
```

### Planned: Flask REST API
```
Client
    ↓ (HTTP POST - JSON)
Flask API (/api/translate/text or /summary)
    ↓ (Audio processing)
Whisper Model + Translation Service
    ↓ (Response)
Client (Transcription/Translation/Summary)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Step-by-Step Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd live-translate-api
   ```

2. **Create and activate a virtual environment**

   **macOS/Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   **Windows:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

   This will install:
   - Flask (3.0.0) - Web framework
   - Flask-CORS (4.0.0) - Cross-origin resource sharing
   - python-dotenv (1.0.0) - Environment variable management
   - openai-whisper - Speech recognition model
   - websockets - WebSocket server/client implementation

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration:
   ```env
   PORT=3000
   # Add translation API keys when ready
   ```

## Usage

### Running the Proof of Concept

The proof of concept demonstrates real-time audio transcription using WebSockets.

1. **Start the WebSocket server**
   ```bash
   python proof-of-concept/proof-of-concept.py
   ```

   Output:
   ```
   Server started on ws://localhost:8765
   ```

2. **Prepare a sample audio file**

   Place an audio file named `sample_audio.m4a` in the `proof-of-concept/` directory. Supported formats include M4A, WAV, MP3, etc.

3. **Run the test client**

   In a separate terminal:
   ```bash
   python proof-of-concept/test_client.py
   ```

   Expected output:
   ```
   Connected to server
   Audio sent
   Received transcription: [Your transcribed text here]
   ```

4. **View results**

   The transcription is also saved to `transcription.txt` in the project root directory.

### Running the Flask API

**Note:** The Flask API is currently under development with placeholder endpoints.

1. **Start the Flask server**
   ```bash
   python app.py
   ```

   The server will start on `http://localhost:3000`

2. **Test the health check endpoint**
   ```bash
   curl http://localhost:3000/health
   ```

   Response:
   ```json
   {
     "status": "ok",
     "timestamp": "2025-09-30T12:00:00.000000"
   }
   ```

### Testing

#### Manual Testing with cURL

**Test the text translation endpoint:**
```bash
curl -X POST http://localhost:3000/api/translate/text \
  -H "Content-Type: application/json" \
  -d '{
    "audio": "base64_encoded_audio_data_here",
    "sourceLanguage": "en",
    "targetLanguage": "es"
  }'
```

**Test the summary endpoint:**
```bash
curl -X POST http://localhost:3000/api/translate/summary \
  -H "Content-Type: application/json" \
  -d '{
    "audio": "base64_encoded_audio_data_here",
    "sourceLanguage": "en",
    "targetLanguage": "es",
    "summaryLength": "medium"
  }'
```

## API Reference

### Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-09-30T12:00:00.000000"
}
```

### Translate to Text

**Endpoint:** `POST /api/translate/text`

**Description:** Transcribe and translate audio to text

**Request Body:**
```json
{
  "audio": "base64_encoded_audio_data",
  "sourceLanguage": "en",
  "targetLanguage": "es"
}
```

**Parameters:**
- `audio` (required): Base64-encoded audio data
- `sourceLanguage` (optional): Source language code (default: "auto")
- `targetLanguage` (optional): Target language code (default: "en")

**Response:**
```json
{
  "success": true,
  "data": {
    "originalLanguage": "en",
    "targetLanguage": "es",
    "translatedText": "Translated text here",
    "timestamp": "2025-09-30T12:00:00.000000"
  }
}
```

### Translate with Summary

**Endpoint:** `POST /api/translate/summary`

**Description:** Transcribe, translate, and summarize audio

**Request Body:**
```json
{
  "audio": "base64_encoded_audio_data",
  "sourceLanguage": "en",
  "targetLanguage": "es",
  "summaryLength": "medium"
}
```

**Parameters:**
- `audio` (required): Base64-encoded audio data
- `sourceLanguage` (optional): Source language code (default: "auto")
- `targetLanguage` (optional): Target language code (default: "en")
- `summaryLength` (optional): Summary length - "short", "medium", or "long" (default: "medium")

**Response:**
```json
{
  "success": true,
  "data": {
    "originalLanguage": "en",
    "targetLanguage": "es",
    "translatedText": "Translated text here",
    "summary": "Summary of the translated content",
    "summaryLength": "medium",
    "timestamp": "2025-09-30T12:00:00.000000"
  }
}
```

**Error Response:**
```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

## Key Technologies

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Primary programming language |
| **Flask** | 3.0.0 | Web framework for REST API |
| **OpenAI Whisper** | Latest | Speech recognition and transcription |
| **WebSockets** | Latest | Real-time bidirectional communication |

### Supporting Libraries

- **Flask-CORS**: Enable cross-origin resource sharing
- **python-dotenv**: Environment variable management
- **asyncio**: Asynchronous I/O operations
- **base64**: Audio data encoding/decoding
- **tempfile**: Temporary file management

### Why These Technologies?

**OpenAI Whisper:**
- State-of-the-art speech recognition
- Multi-language support out of the box
- High accuracy across various audio qualities
- Open-source and self-hostable

**Flask:**
- Lightweight and flexible
- Easy to learn and quick to develop with
- Excellent for REST API development
- Large ecosystem of extensions

**WebSockets:**
- Real-time communication
- Low latency for live transcription
- Bidirectional data flow
- Efficient for streaming audio

## Project Structure

```
live-translate-api/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
│
├── routes/
│   └── translate.py           # Translation API routes
│
└── proof-of-concept/
    ├── proof-of-concept.py    # WebSocket transcription server
    └── test_client.py         # WebSocket test client
```

### File Descriptions

- **app.py**: Main Flask application with CORS configuration and route registration
- **routes/translate.py**: Blueprint containing the `/text` and `/summary` endpoints (currently with placeholder logic)
- **proof-of-concept.py**: Functional WebSocket server using Whisper for real-time transcription
- **test_client.py**: Client script to test the WebSocket server with audio files

## Development Roadmap

### Week 1: Foundation ✅ (Current)
- [x] Project setup and environment configuration
- [x] Proof of concept WebSocket server
- [x] OpenAI Whisper integration
- [x] Basic Flask API structure
- [x] Documentation and README

### Week 2-3: Core Implementation 🚧
- [ ] Implement Whisper integration in Flask endpoints
- [ ] Add translation service (e.g., Google Translate, DeepL)
- [ ] Implement summarization logic
- [ ] Error handling and validation
- [ ] Request/response logging

### Week 4: Enhancement and Testing 📋
- [ ] Add support for different audio formats
- [ ] Implement rate limiting
- [ ] Add authentication/API keys
- [ ] Write unit tests
- [ ] Performance optimization
- [ ] Load testing

### Future Considerations 💭
- [ ] Support for real-time streaming via WebSocket in Flask
- [ ] Database integration for storing transcriptions
- [ ] User management and quotas
- [ ] Docker containerization
- [ ] Deployment configuration (AWS, GCP, etc.)
- [ ] Frontend demo application

## Contributing

This is currently a learning project in active development. Contributions, suggestions, and feedback are welcome!

### Areas for Contribution
- Translation service integration
- Summarization algorithm improvements
- Additional language support
- Performance optimizations
- Documentation enhancements

## License

[Specify your license here - e.g., MIT, Apache 2.0, etc.]

---

## Troubleshooting

### Common Issues

**Issue:** `RuntimeError: no running event loop`
- **Solution:** Ensure you're using `asyncio.run()` instead of `asyncio.get_event_loop()` (fixed in current version)

**Issue:** `fp16 not supported`
- **Solution:** Add `fp16=False` parameter to `model.transcribe()` for CPU compatibility (fixed in current version)

**Issue:** WebSocket connection fails
- **Solution:** Ensure the server is running on `localhost:8765` and no firewall is blocking the connection

**Issue:** Audio file not found
- **Solution:** Place your audio file in the `proof-of-concept/` directory and ensure it's named `sample_audio.m4a`

## Support

For questions, issues, or suggestions:
- Open an issue in the repository
- Contact: [Your contact information]

---

**Project Status:** Active Development | Last Updated: September 30, 2025
