"""
Transcription service using the tarteel-ai/whisper-base-ar-quran model.
"""

import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import numpy as np
from typing import Dict, List, Optional
import logging

from app.audio_processor import audio_processor
from app.quran_data import quran_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
            
            # Process audio for the model
            input_features = self.processor(
                audio_array,
                sampling_rate=sample_rate,
                return_tensors="pt"
            ).input_features
            
            # Move to device
            input_features = input_features.to(self.device)
            
            # Generate transcription with timestamps
            with torch.no_grad():
                predicted_ids = self.model.generate(
                    input_features,
                    return_timestamps=True
                )
            
            # Decode the transcription
            transcription = self.processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True
            )[0]
            
            logger.info(f"Transcription: {transcription}")
            
            # Get timestamps if available
            timestamps = self._extract_timestamps(predicted_ids, audio_array, sample_rate)
            
            # Match verses and create detailed response
            details = self._create_verse_details(transcription, timestamps)
            
            return {
                "success": True,
                "data": {
                    "exact_transcription": transcription,
                    "details": details
                }
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_timestamps(self, predicted_ids: torch.Tensor, 
                          audio_array: np.ndarray, 
                          sample_rate: int) -> List[Dict]:
        """
        Extract word-level timestamps from the model output.
        
        Args:
            predicted_ids: Model output token IDs
            audio_array: Original audio array
            sample_rate: Sample rate
            
        Returns:
            List of timestamp dictionaries
        """
        # This is a simplified version. The actual implementation would need
        # to use the model's timestamp tokens properly.
        # For now, we'll create approximate timestamps based on audio length
        
        audio_duration = len(audio_array) / sample_rate
        
        # Decode to get words
        transcription = self.processor.batch_decode(
            predicted_ids,
            skip_special_tokens=True
        )[0]
        
        words = transcription.split()
        num_words = len(words)
        
        if num_words == 0:
            return []
        
        # Create approximate timestamps (evenly distributed)
        # In production, use actual word-level timestamps from the model
        timestamps = []
        time_per_word = audio_duration / num_words
        
        for i, word in enumerate(words):
            start_time = i * time_per_word
            end_time = (i + 1) * time_per_word
            timestamps.append({
                "word": word,
                "start": start_time,
                "end": end_time
            })
        
        return timestamps
    
    def _create_verse_details(self, transcription: str, 
                            timestamps: List[Dict]) -> List[Dict]:
        """
        Create detailed verse information from transcription and timestamps.
        
        Args:
            transcription: Full transcription text
            timestamps: Word-level timestamps
            
        Returns:
            List of verse detail dictionaries
        """
        # This is a simplified implementation
        # In production, use proper Quran verse matching with a database
        
        # For demonstration, we'll create a basic structure
        # In reality, you'd match the transcription against a Quran database
        
        if not timestamps:
            return []
        
        # Example: Treat the entire transcription as one verse
        # In production, split by actual verse boundaries
        details = []
        
        # This is placeholder logic - replace with actual verse matching
        # using a proper Quran database (e.g., tanzil, quran-json)
        
        # For now, create a single entry as an example
        if transcription.strip():
            start_time = timestamps[0]["start"] if timestamps else 0.0
            end_time = timestamps[-1]["end"] if timestamps else 0.0
            
            # Placeholder verse details
            # In production, match transcription to actual Quran verses
            detail = {
                "surah_number": 1,  # Placeholder
                "ayah_number": 1,   # Placeholder
                "ayah_text_tashkeel": transcription,  # Should be matched to actual verse
                "ayah_word_count": len(transcription.split()),
                "start_from_word": 1,
                "end_to_word": len(transcription.split()),
                "audio_start_timestamp": quran_data._format_timestamp(start_time),
                "audio_end_timestamp": quran_data._format_timestamp(end_time)
            }
            details.append(detail)
        
        return details


# Singleton instance
transcription_service = TranscriptionService()
