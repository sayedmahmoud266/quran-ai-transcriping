"""
Audio Loader Utility - Loads and prepares audio files.

This module handles audio file loading with format conversion and validation.
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


def load_audio_file(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load audio file into memory.
    
    This function ONLY loads the audio data without any processing.
    Resampling should be done in the AudioResamplingStep of the pipeline.
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        Tuple of (audio_array, original_sample_rate)
    """
    logger.info(f"Loading audio file: {file_path}")
    
    # Get file extension
    file_ext = Path(file_path).suffix.lower()
    
    # Load audio
    if file_ext == '.mp3':
        logger.info("MP3 file detected, using pydub for reliable loading...")
        audio_array, sample_rate = _load_with_pydub(file_path)
    else:
        try:
            # Load without resampling to preserve original quality
            audio_array, sample_rate = librosa.load(
                file_path,
                sr=None,  # Keep original sample rate
                mono=True,
                duration=None  # Load entire file
            )
            logger.info(f"Loaded audio: {sample_rate}Hz, {len(audio_array)} samples, {len(audio_array)/sample_rate:.2f}s")
        except Exception as e:
            logger.info(f"Librosa failed, trying pydub: {e}")
            audio_array, sample_rate = _load_with_pydub(file_path)
    
    logger.info(f"Audio loaded successfully: {sample_rate}Hz, {len(audio_array)/sample_rate:.2f}s")
    
    return audio_array, sample_rate


def _load_with_pydub(file_path: str) -> Tuple[np.ndarray, int]:
    """
    Load audio using pydub (handles formats librosa might not support).
    
    Converts to mono but preserves original sample rate.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Tuple of (audio_array, original_sample_rate)
    """
    # Load with pydub
    audio = AudioSegment.from_file(file_path)
    
    # Get original sample rate
    original_sample_rate = audio.frame_rate
    
    # Convert to mono if stereo
    if audio.channels > 1:
        audio = audio.set_channels(1)
    
    # Export to temporary WAV file (preserving sample rate)
    temp_dir = tempfile.gettempdir()
    temp_wav = os.path.join(temp_dir, f"temp_{os.getpid()}.wav")
    audio.export(temp_wav, format="wav")
    
    try:
        # Load the converted file with librosa (keep original sample rate)
        audio_array, sample_rate = librosa.load(
            temp_wav,
            sr=None,  # Keep original sample rate
            mono=True
        )
        return audio_array, sample_rate
    finally:
        # Clean up temporary file
        if os.path.exists(temp_wav):
            os.remove(temp_wav)


def validate_audio(audio_array: np.ndarray, sample_rate: int = 16000) -> bool:
    """
    Validate that audio array is suitable for processing.
    
    Args:
        audio_array: Audio data as numpy array
        sample_rate: Sample rate
        
    Returns:
        True if valid, False otherwise
    """
    if audio_array is None or len(audio_array) == 0:
        return False
    
    # Check if audio is too short (less than 0.1 seconds)
    if len(audio_array) < sample_rate * 0.1:
        return False
    
    return True


def get_audio_duration(audio_array: np.ndarray, sample_rate: int) -> float:
    """
    Get audio duration in seconds.
    
    Args:
        audio_array: Audio data
        sample_rate: Sample rate
        
    Returns:
        Duration in seconds
    """
    return len(audio_array) / sample_rate
