# Live Translate API

A real-time audio transcription and translation API built with Flask and OpenAI Whisper. This project enables live speech-to-text transcription with Voice Activity Detection (VAD), live streaming updates, and translation capabilities.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Status](#project-status)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
  - [Running the Flask API](#running-the-flask-api)
  - [Live Transcription Client](#live-transcription-client)
  - [Testing](#testing)
- [API Reference](#api-reference)
- [Key Technologies](#key-technologies)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Development Roadmap](#development-roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview

Live Translate API is a RESTful service designed to provide real-time audio transcription capabilities with live updates. The project uses OpenAI's Whisper model for accurate speech recognition and supports streaming audio from microphones with intelligent Voice Activity Detection.

**Current Status:** Core transcription features implemented with live streaming support.

## Features

### ✅ Implemented Features
- **Live Audio Transcription** - Real-time speech-to-text via microphone input
- **Voice Activity Detection (VAD)** - WebRTC VAD for intelligent speech detection
- **Live Streaming Updates** - Transcription updates every 1.5 seconds while speaking
- **Paragraph Format Output** - Continuous text display with word wrapping
- **Queue-based Audio Processing** - Efficient multi-threaded audio accumulation
- **Configurable Parameters** - Adjustable VAD mode, silence duration, and update intervals
- **Graceful Shutdown** - Press 'q' + Enter or Ctrl+C to stop
- **Server-Sent Events (SSE)** - Streaming transcription results from server
- **Whisper Model Integration** - Using OpenAI Whisper "base" model for transcription

### 🚧 In Development
- Translation between languages
- Speaker diarization capabilities
- Additional Whisper model options (small, medium, large)

### 📋 Planned Features
- Multi-language support with auto-detection
- Speaker identification and segmentation
- Translation service integration (Google Translate, DeepL)
- Docker containerization
- Database storage for transcriptions

## Project Status

**Phase:** Core Implementation ✅ | Enhancement 🚧

Current implementation includes:
- Fully functional `/transcription` endpoint for live transcription
- Client application with VAD and live updates
- Real-time paragraph-format display
- Production-ready audio processing pipeline

## Architecture

### Current: Live Transcription System

```
Microphone
    ↓
PyAudio (16kHz, 16-bit PCM)
    ↓
WebRTC VAD (Mode 2) - Speech Detection
    ↓
Queue-based Audio Accumulator
    ↓ (Every 1.5s while speaking)
Flask API (/api/translate/transcription)
    ↓
Whisper Model (base)
    ↓ (SSE Stream)
Client Display (Paragraph format)
```

### Multi-threaded Client Architecture

```
Main Thread
    ├── Audio Callback Thread (VAD + Queuing)
    ├── Audio Processor Thread (Accumulation + HTTP requests)
    ├── Keyboard Listener Thread (Quit handler)
    └── Display Updates (Screen refresh)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Microphone for live transcription
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
   - numpy - Audio processing
   - pyaudio - Microphone audio capture
   - webrtcvad - Voice Activity Detection
   - gunicorn (21.2.0) - Production server

4. **Configure environment variables (optional)**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your configuration:
   ```env
   PORT=3000
   ```

## Usage

### Running the Flask API

1. **Start the Flask server**
   ```bash
   python app.py
   ```

   The server will start on `http://localhost:3000`

   You should see:
   ```
   Loading Whisper model...
   Whisper model loaded successfully
   * Running on http://0.0.0.0:3000
   ```

2. **Test the health check endpoint**
   ```bash
   curl http://localhost:3000/health
   ```

   Response:
   ```json
   {
     "status": "ok",
     "timestamp": "2025-10-06T12:00:00.000000"
   }
   ```

### Live Transcription Client

The `test_stream.py` client provides live microphone transcription with real-time updates.

1. **Ensure Flask server is running** (see above)

2. **Run the live transcription client**
   ```bash
   python test_stream.py
   ```

   You'll see:
   ```
   Starting live audio capture...
   Sample rate: 16000 Hz
   VAD mode: 2 (aggressiveness)
   Live updates every: 1.5s
   Listening for speech... (Press 'q' + Enter or Ctrl+C to stop)
   ```

3. **Start speaking** into your microphone

   - Speech detection activates automatically
   - Transcription updates every 1.5 seconds while speaking
   - After 2 seconds of silence, the segment is finalized
   - All text is displayed in paragraph format with word wrapping

4. **Stop the client**
   - Press `q` + Enter for graceful shutdown
   - Or press `Ctrl+C`

   Final transcription will be displayed:
   ```
   ================================================================================
   FINAL TRANSCRIPTION
   ================================================================================

   Your complete transcribed text will appear here in paragraph format...

   ================================================================================

   Audio capture stopped.
   ```

### Testing

#### Manual Testing with cURL

**Test the transcription endpoint with raw audio:**
```bash
# Record 3 seconds of audio and send to server
sox -d -r 16000 -c 1 -b 16 -e signed-integer -t raw - trim 0 3 | \
curl -X POST http://localhost:3000/api/translate/transcription \
  -H "Content-Type: application/octet-stream" \
  -H "X-Source-Language: en" \
  -H "X-Sample-Rate: 16000" \
  --data-binary @-
```

## API Reference

### Health Check

**Endpoint:** `GET /health`

**Description:** Check if the API is running

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-10-06T12:00:00.000000"
}
```

### Live Transcription

**Endpoint:** `POST /api/translate/transcription`

**Description:** Transcribe raw audio bytes to verbatim text with Server-Sent Events streaming

**Request Headers:**
- `Content-Type: application/octet-stream` (required)
- `X-Source-Language: <language_code>` (optional, default: "auto")
- `X-Target-Language: <language_code>` (optional, default: "en", not yet used)
- `X-Sample-Rate: <sample_rate>` (optional, default: "16000")

**Request Body:**
- Raw 16-bit PCM audio bytes (mono channel)

**Response:**
Server-Sent Events (SSE) stream with JSON objects:

```
data: {"type": "status", "message": "Ready to transcribe"}

data: {"type": "transcription", "text": "Hello world", "is_final": true, "timestamp": "2025-10-06T12:00:00.000000"}

data: {"type": "final", "text": "Hello world", "timestamp": "2025-10-06T12:00:00.000000"}
```

**Response Event Types:**
- `status` - Initial ready message
- `transcription` - Partial or final transcription result
- `final` - Complete transcription
- `error` - Error message

**Example Response:**
```json
{"type": "transcription", "text": "Hello world", "is_final": true, "timestamp": "2025-10-06T12:00:00.000000"}
{"type": "final", "text": "Hello world", "timestamp": "2025-10-06T12:00:00.000000"}
```

**Error Responses:**
```json
{"type": "error", "message": "Audio too short"}
```

### Speaker Diarization (Not Yet Implemented)

**Endpoint:** `POST /api/translate/diarization`

**Status:** Placeholder - Returns TODO messages

This endpoint is planned for future implementation with speaker diarization features to identify and segment different speakers in audio.

## Key Technologies

### Core Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Primary programming language |
| **Flask** | 3.0.0 | Web framework for REST API |
| **OpenAI Whisper** | Latest | Speech recognition and transcription |
| **PyAudio** | Latest | Real-time audio capture from microphone |
| **WebRTC VAD** | 2.0.10 | Voice Activity Detection |
| **NumPy** | Latest | Audio data processing |

### Supporting Libraries

- **Flask-CORS**: Enable cross-origin resource sharing
- **python-dotenv**: Environment variable management
- **requests**: HTTP client for SSE streaming
- **threading**: Multi-threaded audio processing
- **queue**: Thread-safe audio buffering

### Why These Technologies?

**OpenAI Whisper:**
- State-of-the-art speech recognition
- Multi-language support out of the box
- High accuracy across various audio qualities
- Open-source and self-hostable

**PyAudio + WebRTC VAD:**
- Real-time microphone capture
- Intelligent speech detection
- Low-latency processing
- Industry-standard VAD algorithm

**Flask + SSE:**
- Lightweight REST API
- Server-Sent Events for streaming
- Easy integration and deployment
- Production-ready with gunicorn

## Project Structure

```
live-translate-api/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker container configuration
├── docker-compose.yml          # Docker compose setup
├── .env.example               # Environment variable template
├── .gitignore                 # Git ignore rules
│
├── routes/
│   └── translate.py           # Translation API routes (/verbatim, /summary)
│
├── test_stream.py             # Live transcription client with VAD
├── live_transcribe_try.py     # Local transcription experiment
│
└── proof-of-concept/
    ├── proof-of-concept.py    # WebSocket transcription server (legacy)
    └── test_client.py         # WebSocket test client (legacy)
```

### File Descriptions

#### Core Application
- **app.py**: Main Flask application with CORS, Whisper model initialization, and route registration
- **routes/translate.py**: Blueprint containing `/transcription` (implemented) and `/diarization` (placeholder) endpoints

#### Client Tools
- **test_stream.py**: Live transcription client with:
  - WebRTC VAD for speech detection
  - Queue-based audio accumulation
  - Live updates every 1.5 seconds
  - Paragraph format display
  - Keyboard controls (q to quit)

- **live_transcribe_try.py**: Experimental local transcription script using speech_recognition library

#### Legacy (Proof of Concept)
- **proof-of-concept/**: Original WebSocket-based implementation (kept for reference)

## Configuration

### Audio Parameters (test_stream.py)

```python
# Audio recording
SAMPLE_RATE = 16000              # 16kHz audio
CHUNK_DURATION_MS = 30           # 30ms chunks for VAD
FORMAT = pyaudio.paInt16         # 16-bit PCM
CHANNELS = 1                     # Mono

# Voice Activity Detection
VAD_MODE = 2                     # 0=least aggressive, 3=most aggressive
SILENCE_DURATION_MS = 2000       # 2 seconds silence ends phrase

# Live transcription
TRANSCRIPTION_UPDATE_INTERVAL = 1.5  # Update every 1.5s while speaking
MIN_AUDIO_LENGTH = 0.5           # Minimum 0.5s audio to transcribe
```

### Server Configuration (routes/translate.py)

```python
# Whisper model
whisper_model = whisper.load_model("base")  # Options: tiny, base, small, medium, large

# Transcription parameters
sample_rate = 16000              # Expected audio sample rate
min_audio_length = 0.5           # Minimum audio length in seconds
```

### Adjusting VAD Aggressiveness

VAD Mode affects speech detection sensitivity:
- **Mode 0**: Least aggressive - allows more background noise, rarely cuts speech
- **Mode 1**: Low - balanced for normal environments
- **Mode 2**: Medium - good for somewhat noisy environments (default)
- **Mode 3**: Most aggressive - strict speech detection, may cut soft speech

To change, edit `VAD_MODE` in `test_stream.py`:
```python
VAD_MODE = 1  # Try less aggressive mode
```

## Development Roadmap

### ✅ Phase 1: Core Transcription (Completed)
- [x] Flask API with `/transcription` endpoint
- [x] Whisper model integration
- [x] Live transcription client with VAD
- [x] Queue-based audio processing
- [x] Server-Sent Events streaming
- [x] Paragraph format display
- [x] Multi-threaded architecture

### 🚧 Phase 2: Enhancement (In Progress)
- [ ] Multiple Whisper model size options
- [ ] Improved error handling and retry logic
- [ ] Audio quality indicators
- [ ] Confidence scores in transcription
- [ ] Docker deployment configuration
- [ ] Unit tests and integration tests

### 📋 Phase 3: Translation & Diarization
- [ ] Translation service integration (Google Translate, DeepL)
- [ ] Implement `/diarization` endpoint with speaker identification
- [ ] Multi-language support
- [ ] Language auto-detection improvements
- [ ] Speaker segmentation and labeling

### 💭 Future Considerations
- [ ] Database integration for storing transcriptions
- [ ] User authentication and API keys
- [ ] Rate limiting and quotas
- [ ] WebSocket support for true bidirectional streaming
- [ ] Frontend demo application
- [ ] Cloud deployment (AWS, GCP, Azure)
- [ ] Performance monitoring and analytics

## Contributing

This project is in active development. Contributions, suggestions, and feedback are welcome!

### Areas for Contribution
- Translation service integration
- Speaker diarization implementation
- Additional Whisper model configurations
- Performance optimizations
- Documentation enhancements
- Testing coverage

### How to Contribute
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

[Specify your license here - e.g., MIT, Apache 2.0, etc.]

---

## Troubleshooting

### Common Issues

**Issue:** `ModuleNotFoundError: No module named 'pyaudio'`
- **Solution:** Install PyAudio: `pip install pyaudio`
- **macOS:** May need `brew install portaudio` first
- **Linux:** May need `sudo apt-get install portaudio19-dev python3-pyaudio`

**Issue:** `OSError: [Errno -9996] Invalid input device`
- **Solution:** Check microphone permissions and that a microphone is connected
- **macOS:** Grant microphone access in System Preferences → Security & Privacy

**Issue:** `fp16 not supported`
- **Solution:** Already handled - code uses `fp16=False` for CPU compatibility

**Issue:** No speech detected
- **Solution:**
  - Check microphone is working: `python -c "import pyaudio; p=pyaudio.PyAudio(); print(p.get_default_input_device_info())"`
  - Try lowering VAD mode: `VAD_MODE = 1` in test_stream.py
  - Speak louder or closer to microphone

**Issue:** Transcription is inaccurate
- **Solution:**
  - Use better Whisper model: Change `base` to `small` or `medium` in routes/translate.py
  - Lower VAD aggressiveness to capture more speech
  - Increase silence duration for longer phrases
  - Ensure quiet environment

**Issue:** Server timeout
- **Solution:** Increase timeout in test_stream.py: `timeout=60` (currently 30s)

**Issue:** Screen not clearing properly
- **Solution:** Terminal compatibility issue - try different terminal emulator

## Performance Notes

### Whisper Model Comparison

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| tiny | 39 MB | Fastest | Lower | Quick testing |
| base | 74 MB | Fast | Good | Current default |
| small | 244 MB | Medium | Better | Recommended |
| medium | 769 MB | Slow | High | High accuracy needs |
| large | 1550 MB | Slowest | Highest | Production quality |

To change model, edit `routes/translate.py`:
```python
whisper_model = whisper.load_model("small")  # Change from "base"
```

### Recommended Settings

**For best accuracy:**
- Model: `small` or `medium`
- VAD Mode: `1` or `2`
- Silence Duration: `2000-3000ms`
- Update Interval: `2.0s`

**For fastest response:**
- Model: `tiny` or `base`
- VAD Mode: `2` or `3`
- Silence Duration: `1000-1500ms`
- Update Interval: `1.0s`

## Support

For questions, issues, or suggestions:
- Open an issue in the repository
- Check existing issues for solutions
- Review the troubleshooting section above

---

**Project Status:** Active Development | Last Updated: October 6, 2025
