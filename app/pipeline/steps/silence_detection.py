"""
Silence Detection Step - Step 2 of the pipeline.

Detects silence in audio and splits into chunks.
"""

from app.pipeline.base import PipelineStep, PipelineContext
from typing import List, Dict, Any
import numpy as np


class SilenceDetectionStep(PipelineStep):
    """
    Detect silence in audio and split into chunks.
    
    Input (from context):
        - audio_array: Audio data
        - sample_rate: Sample rate
    
    Output (to context):
        - chunks: List of audio chunks with metadata
          Each chunk: {
              'audio': np.ndarray,
              'start_time': float,
              'end_time': float,
              'duration': float,
              'chunk_index': int
          }
    """
    
    def __init__(self, 
                 min_silence_len: int = 500,
                 silence_thresh: int = -40,
                 keep_silence: int = 200):
        """
        Initialize silence detection step.
        
        Args:
            min_silence_len: Minimum silence length in ms (default: 500ms)
            silence_thresh: Silence threshold in dBFS (default: -40)
            keep_silence: Amount of silence to keep at edges in ms (default: 200ms)
        """
        super().__init__()
        self.min_silence_len = min_silence_len
        self.silence_thresh = silence_thresh
        self.keep_silence = keep_silence
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that audio data is present."""
        if context.audio_array is None:
            self.logger.error("No audio data in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Detect silence and split audio into chunks.
        
        Args:
            context: Pipeline context with audio data
            
        Returns:
            Context with audio chunks
        """
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        
        audio_array = context.audio_array
        sample_rate = context.sample_rate
        
        self.logger.info(
            f"Detecting silence (min_len={self.min_silence_len}ms, "
            f"thresh={self.silence_thresh}dBFS)"
        )
        
        # Convert numpy array to pydub AudioSegment
        audio_int16 = (audio_array * 32767).astype(np.int16)
        audio_segment = AudioSegment(
            audio_int16.tobytes(),
            frame_rate=sample_rate,
            sample_width=audio_int16.dtype.itemsize,
            channels=1
        )
        
        # Detect non-silent chunks
        nonsilent_ranges = detect_nonsilent(
            audio_segment,
            min_silence_len=self.min_silence_len,
            silence_thresh=self.silence_thresh,
            seek_step=10
        )
        
        # Convert to chunks
        chunks = []
        
        if not nonsilent_ranges:
            # No silence detected, return entire audio as one chunk
            chunks.append({
                'audio': audio_array,
                'start_time': 0.0,
                'end_time': len(audio_array) / sample_rate,
                'duration': len(audio_array) / sample_rate,
                'chunk_index': 0
            })
        else:
            for idx, (start_ms, end_ms) in enumerate(nonsilent_ranges):
                # Add silence padding
                start_ms = max(0, start_ms - self.keep_silence)
                end_ms = min(len(audio_segment), end_ms + self.keep_silence)
                
                # Convert to sample indices
                start_sample = int(start_ms * sample_rate / 1000)
                end_sample = int(end_ms * sample_rate / 1000)
                
                # Extract chunk
                chunk_audio = audio_array[start_sample:end_sample]
                
                # Only include chunks that are long enough (at least 0.1s)
                if len(chunk_audio) >= sample_rate * 0.1:
                    chunks.append({
                        'audio': chunk_audio,
                        'start_time': start_sample / sample_rate,
                        'end_time': end_sample / sample_rate,
                        'duration': len(chunk_audio) / sample_rate,
                        'chunk_index': idx
                    })
        
        # Update context
        context.chunks = chunks
        
        self.logger.info(f"Detected {len(chunks)} audio chunks")
        
        # Add debug info
        context.add_debug_info(self.name, {
            'total_chunks': len(chunks),
            'chunks': [{
                'chunk_index': c['chunk_index'],
                'start_time': c['start_time'],
                'end_time': c['end_time'],
                'duration': c['duration']
            } for c in chunks]
        })
        
        return context
