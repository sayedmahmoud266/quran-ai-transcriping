"""
Audio Resampling Step - Step 1 of the pipeline.

Resamples audio to 16kHz for Whisper model compatibility.
"""

from app.pipeline.base import PipelineStep, PipelineContext
import numpy as np


class AudioResamplingStep(PipelineStep):
    """
    Resample audio to target sample rate (16kHz for Whisper).
    
    Input (from context):
        - audio_array: Raw audio data
        - sample_rate: Current sample rate
    
    Output (to context):
        - audio_array: Resampled audio data
        - sample_rate: Target sample rate (16000)
        - metadata['original_sample_rate']: Original sample rate
        - metadata['audio_duration']: Audio duration in seconds
    """
    
    def __init__(self, target_sample_rate: int = 16000):
        """
        Initialize the audio resampling step.
        
        Args:
            target_sample_rate: Target sample rate (default: 16000 for Whisper)
        """
        super().__init__()
        self.target_sample_rate = target_sample_rate
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that audio data is present."""
        if context.audio_array is None:
            self.logger.error("No audio data in context")
            return False
        
        if context.sample_rate <= 0:
            self.logger.error("Invalid sample rate")
            return False
        
        return True
    
    def should_skip(self, context: PipelineContext) -> bool:
        """Skip if already at target sample rate."""
        return context.sample_rate == self.target_sample_rate
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Resample audio to target sample rate.
        
        Args:
            context: Pipeline context with audio data
            
        Returns:
            Context with resampled audio
        """
        import librosa
        
        original_sr = context.sample_rate
        audio_array = context.audio_array
        
        self.logger.info(f"Resampling from {original_sr}Hz to {self.target_sample_rate}Hz")
        
        # Resample using librosa's high-quality resampler
        resampled_audio = librosa.resample(
            audio_array,
            orig_sr=original_sr,
            target_sr=self.target_sample_rate,
            res_type='kaiser_best'
        )
        
        # Update context
        context.audio_array = resampled_audio
        context.sample_rate = self.target_sample_rate
        context.set('original_sample_rate', original_sr)
        context.set('audio_duration', len(resampled_audio) / self.target_sample_rate)
        
        self.logger.info(
            f"Resampled audio: {len(resampled_audio)} samples, "
            f"{context.get('audio_duration'):.2f}s"
        )
        
        # Add debug info
        context.add_debug_info(self.name, {
            'original_sample_rate': original_sr,
            'target_sample_rate': self.target_sample_rate,
            'original_samples': len(audio_array),
            'resampled_samples': len(resampled_audio),
            'duration_seconds': context.get('audio_duration')
        })
        
        return context
