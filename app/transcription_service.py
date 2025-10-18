"""
Transcription service using the tarteel-ai/whisper-base-ar-quran model.

This module provides the core transcription functionality.
The processing pipeline has been removed and needs to be reimplemented.
"""

import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import numpy as np
from typing import Dict
import logging

from app.audio_processor import audio_processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global debug recorder (set by background worker)
_debug_recorder = None

def set_debug_recorder(recorder):
    """Set the global debug recorder."""
    global _debug_recorder
    _debug_recorder = recorder


class TranscriptionService:
    """
    Service for transcribing Quran recitations using the Whisper model.
    """
    
    MODEL_NAME = "tarteel-ai/whisper-base-ar-quran"
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the Whisper model and processor."""
        try:
            logger.info(f"Loading model: {self.MODEL_NAME}")
            
            # Determine device (GPU if available, else CPU)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")
            
            # Load processor and model
            self.processor = WhisperProcessor.from_pretrained(self.MODEL_NAME)
            self.model = WhisperForConditionalGeneration.from_pretrained(self.MODEL_NAME)
            self.model.to(self.device)
            
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def transcribe_audio(self, audio_array: np.ndarray, sample_rate: int) -> Dict:
        """
        Transcribe audio to Quran text with timestamps.
        
        PLACEHOLDER: This method needs to be reimplemented with the new processing pipeline.
        
        The new pipeline should include the following steps:
        1. audio_resampled - Resample audio to 16kHz
        2. silence_detected - Detect silence in audio
        3. chunks_merged - Merge small chunks together
        4. chunks_transcribed - Transcribe each chunk
        5. duplicates_removed - Remove duplicate words between chunks
        6. timestamps_combined - Combine timestamps from chunks
        7. verses_matched - Match transcription to Quran verses
        8. timestamps_calculated - Calculate accurate timestamps for each verse
        9. silence_splitting - Split silence between verses
        10. audio_splitting - Split audio into individual verse files
        
        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate of the audio
            
        Returns:
            Dictionary with transcription results
        """
        try:
            # Validate audio
            if not audio_processor.validate_audio(audio_array):
                raise ValueError("Invalid audio data")
            
            logger.info("Processing audio for transcription...")
            logger.info(f"Audio duration: {len(audio_array)/sample_rate:.2f}s")
            
            # TODO: Implement new processing pipeline here
            # The old pipeline has been removed. Please implement the new algorithm.
            
            return {
                "success": False,
                "error": "Processing pipeline not yet implemented. Please implement the new algorithm."
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # TODO: Add new pipeline methods here
    # Examples:
    # - _detect_silence()
    # - _merge_chunks()
    # - _transcribe_chunk()
    # - _remove_duplicates()
    # - _match_verses()
    # - _calculate_timestamps()
    # - _split_by_silence()
    # - _split_audio_by_verses()


# Singleton instance
transcription_service = TranscriptionService()
