"""
Inference Module - Machine learning model management.

This module contains all inference-related services:
- Transcription (Whisper model)
- Additional models for the new algorithm
"""

from app.inference.transcription import TranscriptionService, transcription_service

__all__ = ['TranscriptionService', 'transcription_service']
