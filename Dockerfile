# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing and building Python packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gcc \
    g++ \
    make \
    portaudio19-dev \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for temporary files
RUN mkdir -p /tmp/audio

# Expose port
EXPOSE 3000

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/models
ENV TRANSFORMERS_CACHE=/models

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Run the application with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:3000", "--workers", "1", "--timeout", "300", "--worker-class", "sync", "app:app"]
