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


def load_audio_file(file_path: str, target_sample_rate: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Load audio file and prepare for processing.
    
    Handles multiple formats and resamples to target sample rate.
    Adds silence buffer at the end for complete transcription.
    
    Args:
        file_path: Path to the audio file
        target_sample_rate: Target sample rate (default: 16000 for Whisper)
        
    Returns:
        Tuple of (audio_array, sample_rate)
    """
    logger.info(f"Loading audio file: {file_path}")
    
    # Get file extension
    file_ext = Path(file_path).suffix.lower()
    
    # Load audio
    if file_ext == '.mp3':
        logger.info("MP3 file detected, using pydub for reliable loading...")
        audio_array, original_sr = _load_with_pydub(file_path, target_sample_rate)
    else:
        try:
            # Load without resampling to preserve quality
            audio_array, original_sr = librosa.load(
                file_path,
                sr=None,  # Keep original sample rate
                mono=True,
                duration=None  # Load entire file
            )
            logger.info(f"Loaded audio: {original_sr}Hz, {len(audio_array)} samples")
        except Exception as e:
            logger.info(f"Librosa failed, trying pydub: {e}")
            audio_array, original_sr = _load_with_pydub(file_path, target_sample_rate)
    
    # Resample if needed
    if original_sr != target_sample_rate:
        logger.info(f"Resampling from {original_sr}Hz to {target_sample_rate}Hz...")
        audio_array = librosa.resample(
            audio_array,
            orig_sr=original_sr,
            target_sr=target_sample_rate,
            res_type='kaiser_best'
        )
        sample_rate = target_sample_rate
    else:
        sample_rate = original_sr
    
    # Add silence buffer at the end
    silence_duration = 3.0  # seconds
    silence_samples = int(silence_duration * sample_rate)
    silence = np.zeros(silence_samples, dtype=audio_array.dtype)
    audio_array = np.concatenate([audio_array, silence])
    
    logger.info(f"Final audio: {sample_rate}Hz, {len(audio_array)/sample_rate:.2f}s")
    
    return audio_array, sample_rate


def _load_with_pydub(file_path: str, target_sample_rate: int) -> Tuple[np.ndarray, int]:
    """
    Load audio using pydub (handles formats librosa might not support).
    
    Args:
        file_path: Path to audio file
        target_sample_rate: Target sample rate
        
    Returns:
        Tuple of (audio_array, sample_rate)
    """
    # Load with pydub
    audio = AudioSegment.from_file(file_path)
    
    # Convert to mono if stereo
    if audio.channels > 1:
        audio = audio.set_channels(1)
    
    # Resample to target sample rate
    audio = audio.set_frame_rate(target_sample_rate)
    
    # Export to temporary WAV file
    temp_dir = tempfile.gettempdir()
    temp_wav = os.path.join(temp_dir, f"temp_{os.getpid()}.wav")
    audio.export(temp_wav, format="wav")
    
    try:
        # Load the converted file with librosa
        audio_array, sample_rate = librosa.load(
            temp_wav,
            sr=target_sample_rate,
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
