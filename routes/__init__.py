"""
Routes package for Live Translate API
"""
from .transcription import transcription_bp
from .diarization import diarization_bp

__all__ = ['transcription_bp', 'diarization_bp']
