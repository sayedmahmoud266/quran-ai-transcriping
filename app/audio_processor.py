"""
Audio processing module for handling various audio formats and preparing them for transcription.
"""

import os
import tempfile
from pathlib import Path
from typing import Tuple, Optional
import librosa
import soundfile as sf
import numpy as np
from pydub import AudioSegment


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
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Tuple of (audio_array, sample_rate)
        """
        # Get file extension
        file_ext = Path(file_path).suffix.lower()
        
        # Try to load directly with librosa first
        try:
            audio_array, sample_rate = librosa.load(
                file_path, 
                sr=self.TARGET_SAMPLE_RATE,
                mono=True
            )
            return audio_array, sample_rate
        except Exception as e:
            # If librosa fails, try pydub for format conversion
            print(f"Librosa failed, trying pydub: {e}")
            return self._convert_with_pydub(file_path)
    
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


# Singleton instance
audio_processor = AudioProcessor()
