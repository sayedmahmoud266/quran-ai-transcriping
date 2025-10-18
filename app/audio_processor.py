"""
Audio processing module for handling various audio formats and preparing them for transcription.

This module provides basic audio loading and validation.
Pipeline-specific processing methods have been removed and need to be reimplemented.
"""

import os
import tempfile
from pathlib import Path
from typing import Tuple
import librosa
import numpy as np
from pydub import AudioSegment
import logging

logger = logging.getLogger(__name__)

# Global debug recorder (set by background worker)
_debug_recorder = None

def set_debug_recorder(recorder):
    """Set the global debug recorder."""
    global _debug_recorder
    _debug_recorder = recorder


class AudioProcessor:
    """
    Handles audio file processing including format conversion and resampling.
    """
    
    # Target sample rate for Whisper model
    TARGET_SAMPLE_RATE = 16000
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def process_audio_file(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Process audio file to the format required by the Whisper model.
        Loads audio, resamples to 16kHz, and adds silence buffer.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        # Get file extension
        file_ext = Path(file_path).suffix.lower()
        
        # Step 1: Load audio at its original sample rate first
        # For MP3 files, use pydub first as it handles them better than librosa
        if file_ext == '.mp3':
            logger.info("MP3 file detected, using pydub for reliable loading...")
            audio_array, original_sr = self._convert_with_pydub(file_path)
            original_duration = len(audio_array) / original_sr
            logger.info(f"Loaded via pydub: original_sr={original_sr}Hz, duration={original_duration:.2f}s, samples={len(audio_array)}")
        else:
            try:
                # Load without resampling to preserve quality
                # IMPORTANT: duration=None to load entire file
                audio_array, original_sr = librosa.load(
                    file_path, 
                    sr=None,  # Keep original sample rate
                    mono=True,
                    duration=None  # Load entire file, don't truncate
                )
                original_duration = len(audio_array) / original_sr
                logger.info(f"Loaded audio: original_sr={original_sr}Hz, duration={original_duration:.2f}s, samples={len(audio_array)}")
            except Exception as e:
                # If librosa fails, try pydub for format conversion
                logger.info(f"Librosa failed, trying pydub: {e}")
                audio_array, original_sr = self._convert_with_pydub(file_path)
                original_duration = len(audio_array) / original_sr
        
        # Step 2: Resample to target sample rate if needed
        if original_sr != self.TARGET_SAMPLE_RATE:
            logger.info(f"Resampling from {original_sr}Hz to {self.TARGET_SAMPLE_RATE}Hz...")
            audio_array = librosa.resample(
                audio_array, 
                orig_sr=original_sr, 
                target_sr=self.TARGET_SAMPLE_RATE,
                res_type='kaiser_best'  # High quality resampling
            )
            sample_rate = self.TARGET_SAMPLE_RATE
            resampled_duration = len(audio_array) / sample_rate
            logger.info(f"After resampling: duration={resampled_duration:.2f}s, samples={len(audio_array)}")
        else:
            sample_rate = original_sr
            resampled_duration = original_duration
        
        # Step 3: Add silence buffer at the end to ensure complete transcription
        silence_duration = 3.0  # seconds
        silence_samples = int(silence_duration * sample_rate)
        silence = np.zeros(silence_samples, dtype=audio_array.dtype)
        audio_array = np.concatenate([audio_array, silence])
        
        logger.info(f"Added {silence_duration}s silence buffer at end")
        logger.info(f"Final audio: sr={sample_rate}Hz, duration={len(audio_array)/sample_rate:.2f}s")
        
        # Debug: Save resampled audio
        if _debug_recorder:
            _debug_recorder.save_step(
                "01_audio_resampled",
                data={
                    "sample_rate": sample_rate,
                    "duration_seconds": len(audio_array) / sample_rate,
                    "total_samples": len(audio_array),
                    "original_sample_rate": original_sr if 'original_sr' in locals() else sample_rate
                },
                audio_files=[{
                    "name": "resampled_audio",
                    "audio": audio_array
                }],
                sample_rate=sample_rate
            )
        
        return audio_array, sample_rate
    
    def _convert_with_pydub(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Convert audio file using pydub and then load with librosa.
        This handles formats that librosa might not support directly.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        # Load with pydub
        audio = AudioSegment.from_file(file_path)
        
        # Convert to mono if stereo
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Resample to target sample rate
        audio = audio.set_frame_rate(self.TARGET_SAMPLE_RATE)
        
        # Export to temporary WAV file
        temp_wav = os.path.join(self.temp_dir, f"temp_{os.getpid()}.wav")
        audio.export(temp_wav, format="wav")
        
        try:
            # Load the converted file with librosa
            audio_array, sample_rate = librosa.load(
                temp_wav,
                sr=self.TARGET_SAMPLE_RATE,
                mono=True
            )
            return audio_array, sample_rate
        finally:
            # Clean up temporary file
            if os.path.exists(temp_wav):
                os.remove(temp_wav)
    
    def validate_audio(self, audio_array: np.ndarray) -> bool:
        """
        Validate that the audio array is suitable for processing.
        
        Args:
            audio_array: Audio data as numpy array
            
        Returns:
            True if valid, False otherwise
        """
        if audio_array is None or len(audio_array) == 0:
            return False
        
        # Check if audio is too short (less than 0.1 seconds)
        if len(audio_array) < self.TARGET_SAMPLE_RATE * 0.1:
            return False
        
        return True
    
    def get_audio_duration(self, audio_array: np.ndarray, sample_rate: int) -> float:
        """
        Get the duration of audio in seconds.
        
        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate of the audio
            
        Returns:
            Duration in seconds
        """
        return len(audio_array) / sample_rate
    
    # TODO: Add new pipeline methods here
    # Examples:
    # - split_audio_by_silence() - Detect and split by silence
    # - merge_short_chunks() - Merge chunks that are too short
    # - merge_chunks_with_short_silences() - Merge chunks with small gaps


# Singleton instance
audio_processor = AudioProcessor()
