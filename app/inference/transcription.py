"""
Transcription service using the tarteel-ai/whisper-base-ar-quran model.

This module provides model initialization and management.
The actual transcription is handled by the pipeline module.
"""

import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration, GenerationConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Service for transcribing Quran recitations using the Whisper model.
    """
    
    MODEL_NAME = "tarteel-ai/whisper-base-ar-quran"
    BASE_MODEL_NAME = "openai/whisper-base"
    
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
            generation_config = GenerationConfig.from_pretrained(self.BASE_MODEL_NAME)
            self.model.generation_config = generation_config
            self.model.to(self.device)
            
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def get_model_info(self):
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.MODEL_NAME,
            "device": self.device,
            "model_loaded": self.model is not None,
            "processor_loaded": self.processor is not None
        }

    def transcribe_bytes(self, audio_array):
        """
        Transcribe audio array using the Whisper model.
        
        Args:
            audio_array: Numpy array or list of audio samples (float32, 16kHz)
        
        Returns:
            Transcription result dictionary with 'text' key
        """
        try:
            logger.info("Transcribing audio...")
            
            # Use processor to convert audio to input features (mel spectrograms)
            # The processor expects audio at 16kHz sample rate
            input_features = self.processor(
                audio_array, 
                sampling_rate=16000, 
                return_tensors="pt"
            ).input_features
            
            # Move to device
            input_features = input_features.to(self.device)
            
            logger.info(f"Input features shape: {input_features.shape}")
            
            # Generate transcription with timestamps
            predicted_ids = self.model.generate(
                input_features,
                return_timestamps=True
            )
            
            # Decode the transcription
            transcription = self.processor.batch_decode(
                predicted_ids, 
                skip_special_tokens=True
            )
            
            logger.info(f"Transcription completed: {transcription[0]}")
            
            return {
                'text': transcription[0],
                'predicted_ids': predicted_ids
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise



# Singleton instance
transcription_service = TranscriptionService()
