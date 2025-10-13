# Live Translate API

A Flask-based audio transcription and speaker diarization API powered by OpenAI Whisper and Pyannote.audio. This service provides accurate speech-to-text transcription with speaker identification through separate, scalable API endpoints.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
  - [Local Setup](#local-setup)
  - [Docker Setup](#docker-setup)
- [Usage](#usage)
  - [API Endpoints](#api-endpoints)
  - [Testing](#testing)
- [Configuration](#configuration)
- [Limitations](#limitations)
- [Performance Comparison](#performance-comparison)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Overview

Live Translate API is a RESTful service that provides:
- **Chunk-level transcription** using OpenAI Whisper with word-level timestamps
- **Speaker diarization** using Pyannote.audio for identifying who spoke when
- **Flexible architecture** with separate endpoints for scalable deployment

The implementation is inspired by the approach detailed in [Whisper + Pyannote: The Ultimate Solution for Speech Transcription](https://scalastic.io/en/whisper-pyannote-ultimate-speech-transcription/), combining Whisper's transcription capabilities with Pyannote's speaker identification through timestamp-based alignment.

## Features

### ✅ Implemented Features
- **Transcription Endpoint** (`/api/translate/transcription`)
  - OpenAI Whisper large-v3-turbo model
  - Chunk-level timestamps (3-5 second segments)
  - JSON response with full transcription and timestamp data
  - Supports file path input

- **Diarization Endpoint** (`/api/translate/diarization`)
  - Pyannote speaker-diarization-3.1 pipeline
  - Speaker segmentation with time boundaries
  - Automatic speaker counting
  - Device-agnostic (CUDA, MPS, CPU)

- **Live Transcription Client** (`live_transcribe_diarize.py`)
  - Real-time microphone capture with VAD
  - Local Whisper transcription for immediate feedback
  - Post-session diarization with speaker attribution
  - Automatic speaker turn merging

- **Docker Support**
  - Full containerization with Dockerfile
  - Docker Compose configuration
  - Model caching for faster subsequent runs
  - Health check endpoints

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Flask API Server                           │
│                                                                 │
│  ┌───────────────────────┐      ┌──────────────────────────┐    │
│  │ /api/translate/       │      │ /api/translate/          │    │
│  │ transcription         │      │ diarization              │    │
│  │                       │      │                          │    │
│  │ • OpenAI Whisper      │      │ • Pyannote.audio         │    │
│  │ • large-v3-turbo      │      │ • speaker-diarization-3.1│    │
│  │ • Chunk timestamps    │      │ • Speaker segments       │    │
│  └───────────────────────┘      └──────────────────────────┘    │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Health Check: /health                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ↑
                              │ HTTP/JSON
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 Client (live_transcribe_diarize.py)             │
│                                                                 │
│  1. Live Recording → VAD → Local Whisper Display                │
│  2. Save Audio File                                             │
│  3. POST /transcription → Get word chunks                       │
│  4. POST /diarization → Get speaker segments                    │
│  5. Align chunks to speakers → Merge consecutive turns          │
│  6. Display: [Speaker] Text segments                            │
└─────────────────────────────────────────────────────────────────┘
```

### Diarization Pipeline

The diarization pipeline follows a chunk-level alignment approach:

```
Audio File
    ↓
┌─────────────────────────┐
│  Whisper Transcription  │
│  Returns: Chunks        │
│  [{text, [start, end]}] │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│  Pyannote Diarization   │
│  Returns: Segments      │
│  [Speaker, start, end]  │
└─────────────────────────┘
    ↓
┌─────────────────────────────────┐
│  Timestamp-based Alignment      │
│  For each chunk:                │
│    • Calculate overlap with each│
│      speaker segment            │
│    • Assign to speaker with max │
│      intersection               │
└─────────────────────────────────┘
    ↓
┌─────────────────────────┐
│  Merge Consecutive      │
│  Same speaker → combine │
└─────────────────────────┘
    ↓
Speaker-attributed transcript
```

## Installation

### Local Setup

**Prerequisites:**
- Python 3.11+
- FFmpeg (for audio processing)
- HuggingFace account with token (for Pyannote models)

**Steps:**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd live-translate-api
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```env
   PORT=3000
   FLASK_DEBUG=False
   HF_TOKEN=your_huggingface_token_here
   ```

   Get your HuggingFace token from: https://huggingface.co/settings/tokens

5. **Accept Pyannote model terms**
   - Visit https://huggingface.co/pyannote/speaker-diarization-3.1
   - Click "Agree and access repository"

6. **Run the server**
   ```bash
   python app.py
   ```

### Docker Setup

**Prerequisites:**
- Docker
- Docker Compose

**Steps:**

1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your HF_TOKEN
   ```

2. **Build and run**
   ```bash
   docker compose up --build
   ```

3. **Check logs**
   ```bash
   docker compose logs -f
   ```

4. **Stop**
   ```bash
   docker compose down
   ```

## Usage

### API Endpoints

#### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-10-12T20:00:00.000000"
}
```

#### Transcription

```bash
POST /api/translate/transcription
Content-Type: application/json

{
  "audio_path": "/path/to/audio.wav"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "transcription": "Do or do not. There is no try.",
    "timestamps": [
      {
        "text": "Do or do not.",
        "timestamp": [0.0, 2.0]
      },
      {
        "text": "There is no try.",
        "timestamp": [2.0, 7.04]
      }
    ],
    "timestamp": "2025-10-12T20:50:38.837694"
  }
}
```

#### Diarization

```bash
POST /api/translate/diarization
Content-Type: application/json

{
  "audio_path": "/path/to/audio.wav"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "speakers": [
      {
        "speaker_id": "SPEAKER_00",
        "start": 0.0,
        "end": 3.5
      },
      {
        "speaker_id": "SPEAKER_01",
        "start": 3.5,
        "end": 7.0
      }
    ],
    "sourceLanguage": "auto",
    "numSpeakers": 2,
    "timestamp": "2025-10-12T20:50:40.123456"
  }
}
```

### Testing

#### Live Transcription with Diarization

```bash
python live_transcribe_diarize.py
```

This will:
1. Record audio from your microphone
2. Show live transcription in real-time
3. Save the audio file when you stop (Ctrl+C)
4. Run diarization on the saved audio
5. Display speaker-attributed transcript

#### cURL Testing

**Test transcription:**
```bash
curl -X POST http://localhost:3000/api/translate/transcription \
  -H "Content-Type: application/json" \
  -d '{"audio_path": "recording.wav"}'
```

**Test diarization:**
```bash
curl -X POST http://localhost:3000/api/translate/diarization \
  -H "Content-Type: application/json" \
  -d '{"audio_path": "recording.wav"}'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3000` | Flask server port |
| `FLASK_DEBUG` | `False` | Enable debug mode |
| `HF_TOKEN` | Required | HuggingFace API token for Pyannote |

### Whisper Model

Change model in `routes/transcription.py`:
```python
WhisperAudioTranscriber(model_name="openai/whisper-large-v3-turbo")
```

Available models:
- `openai/whisper-tiny`
- `openai/whisper-base`
- `openai/whisper-small`
- `openai/whisper-medium`
- `openai/whisper-large-v2`
- `openai/whisper-large-v3`
- `openai/whisper-large-v3-turbo` (current)

### Pyannote Pipeline

Configure parameters in `routes/diarization.py` after line 156:
```python
pipeline.instantiate({
    'clustering': {
        'threshold': 0.7,  # Lower = more speakers detected
    },
    'segmentation': {
        'threshold': 0.5,  # Lower = more speech detected
    }
})
```

## Limitations

**See [LIMITATIONS.md](LIMITATIONS.md) for detailed accuracy issues.**

Key limitations:
- **Chunk-level timestamps**: 3-5 second chunks may contain multiple speakers
- **Timestamp misalignment**: Whisper and Pyannote timestamps don't perfectly align
- **Speaker changes within chunks**: If speakers change mid-chunk, attribution goes to dominant speaker
- **Overlapping speech**: Both models struggle with simultaneous speakers
- **No forced alignment**: Whisper's native timestamps can be off by ±0.1-0.3 seconds

## Performance Comparison

**See [ACCURACY_COMPARISON.md](ACCURACY_COMPARISON.md) for detailed benchmarks.**

Quick comparison with WhisperX:

| Metric | Current Implementation | WhisperX |
|--------|------------------------|----------|
| Accuracy | ~75-85% | ~90-95% |
| Speed | Medium (CPU) | Fast (GPU) |
| Setup Complexity | Simple (2 endpoints) | Complex (integrated pipeline) |
| Deployment | Docker-ready | Requires GPU |

## Project Structure

```
live-translate-api/
├── app.py                      # Flask application entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── .env.example               # Environment variable template
│
├── routes/
│   ├── transcription.py       # Whisper transcription endpoint
│   └── diarization.py         # Pyannote diarization endpoint
│
├── live_transcribe_diarize.py # Live transcription + diarization client
├── whisperx_test.py           # WhisperX comparison script
│
├── LIMITATIONS.md             # Detailed accuracy limitations
├── ACCURACY_COMPARISON.md     # Performance comparison with WhisperX
└── README.md                  # This file
```

## Key Technologies

| Technology | Version | Purpose |
|------------|---------|---------|
| **Flask** | 3.0.0 | REST API framework |
| **Transformers** | ≥4.40.0 | Whisper model interface |
| **Pyannote.audio** | Latest | Speaker diarization |
| **PyTorch** | ≥2.0.0 | Deep learning backend |
| **Gunicorn** | 21.2.0 | Production WSGI server |

## Contributing

Contributions welcome! Areas for improvement:
- Implement forced alignment (wav2vec2) for better timestamps
- Add word-level diarization option
- Optimize overlap threshold calculations
- Add batch processing support
- Improve error handling

## Acknowledgments

- Real-time audio recording and VAD implementation adapted from [whisper_real_time](https://github.com/davabase/whisper_real_time) by davabase
- Diarization pipeline approach inspired by [Whisper + Pyannote: The Ultimate Solution for Speech Transcription](https://scalastic.io/en/whisper-pyannote-ultimate-speech-transcription/)
- Built with [OpenAI Whisper](https://github.com/openai/whisper) and [Pyannote.audio](https://github.com/pyannote/pyannote-audio)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Last Updated:** October 13, 2025
