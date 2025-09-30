"""
Audio processing module for handling various audio formats and preparing them for transcription.
"""

import os
import tempfile
from pathlib import Path
from typing import Tuple, Optional, List, Dict
import librosa
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent


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
    
    def split_audio_by_silence(
        self, 
        audio_array: np.ndarray, 
        sample_rate: int,
        min_silence_len: int = 500,
        silence_thresh: int = -40,
        keep_silence: int = 200
    ) -> List[Dict]:
        """
        Split audio into chunks based on silence detection.
        
        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate of the audio
            min_silence_len: Minimum length of silence in ms to be considered a split point
            silence_thresh: Silence threshold in dBFS (lower = more sensitive)
            keep_silence: Amount of silence to keep at edges in ms
            
        Returns:
            List of dictionaries containing chunk data and metadata
        """
        # Convert numpy array to pydub AudioSegment for silence detection
        # Normalize to int16 format
        audio_int16 = (audio_array * 32767).astype(np.int16)
        
        # Create AudioSegment from numpy array
        audio_segment = AudioSegment(
            audio_int16.tobytes(),
            frame_rate=sample_rate,
            sample_width=audio_int16.dtype.itemsize,
            channels=1
        )
        
        # Detect non-silent chunks
        nonsilent_ranges = detect_nonsilent(
            audio_segment,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            seek_step=10
        )
        
        chunks = []
        
        # If no silence detected, return the entire audio as one chunk
        if not nonsilent_ranges:
            chunks.append({
                "audio": audio_array,
                "start_time": 0.0,
                "end_time": len(audio_array) / sample_rate,
                "chunk_index": 0
            })
            return chunks
        
        # Process each non-silent range
        for idx, (start_ms, end_ms) in enumerate(nonsilent_ranges):
            # Add some silence padding if requested
            start_ms = max(0, start_ms - keep_silence)
            end_ms = min(len(audio_segment), end_ms + keep_silence)
            
            # Convert milliseconds to sample indices
            start_sample = int(start_ms * sample_rate / 1000)
            end_sample = int(end_ms * sample_rate / 1000)
            
            # Extract chunk
            chunk_audio = audio_array[start_sample:end_sample]
            
            # Only include chunks that are long enough
            if len(chunk_audio) >= sample_rate * 0.1:  # At least 0.1 seconds
                chunks.append({
                    "audio": chunk_audio,
                    "start_time": start_sample / sample_rate,
                    "end_time": end_sample / sample_rate,
                    "chunk_index": idx
                })
        
        return chunks
    
    def merge_short_chunks(
        self, 
        chunks: List[Dict], 
        min_chunk_duration: float = 1.0,
        max_chunk_duration: float = 30.0
    ) -> List[Dict]:
        """
        Merge short chunks together to avoid too many small segments.
        
        Args:
            chunks: List of audio chunks
            min_chunk_duration: Minimum duration for a chunk in seconds
            max_chunk_duration: Maximum duration for a merged chunk in seconds
            
        Returns:
            List of merged chunks
        """
        if not chunks:
            return chunks
        
        merged_chunks = []
        current_merge = None
        
        for chunk in chunks:
            chunk_duration = len(chunk["audio"]) / self.TARGET_SAMPLE_RATE
            
            if current_merge is None:
                current_merge = chunk.copy()
            else:
                current_duration = len(current_merge["audio"]) / self.TARGET_SAMPLE_RATE
                
                # Merge if current chunk is too short or combined duration is acceptable
                if (chunk_duration < min_chunk_duration or current_duration < min_chunk_duration) and \
                   (current_duration + chunk_duration) <= max_chunk_duration:
                    # Merge chunks
                    current_merge["audio"] = np.concatenate([current_merge["audio"], chunk["audio"]])
                    current_merge["end_time"] = chunk["end_time"]
                else:
                    # Save current merge and start new one
                    merged_chunks.append(current_merge)
                    current_merge = chunk.copy()
        
        # Add the last chunk
        if current_merge is not None:
            merged_chunks.append(current_merge)
        
        # Re-index chunks
        for idx, chunk in enumerate(merged_chunks):
            chunk["chunk_index"] = idx
        
        return merged_chunks


# Singleton instance
audio_processor = AudioProcessor()
