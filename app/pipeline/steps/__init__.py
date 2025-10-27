"""
Pipeline steps for Quran AI transcription processing.

Each step is a self-contained unit that performs a specific task in the pipeline.
"""

# Import all step classes for easy access
from app.pipeline.steps.audio_resampling import AudioResamplingStep
from app.pipeline.steps.silence_detection import SilenceDetectionStep
from app.pipeline.steps.chunk_merging import ChunkMergingStep
from app.pipeline.steps.chunk_transcription import ChunkTranscriptionStep
from app.pipeline.steps.duplicate_removal import DuplicateRemovalStep
from app.pipeline.steps.transcription_combining import TranscriptionCombiningStep
from app.pipeline.steps.verse_matching import VerseMatchingStep
from app.pipeline.steps.transcription_alignment import TranscriptionAlignmentStep
from app.pipeline.steps.timestamp_calculation import TimestampCalculationStep
from app.pipeline.steps.silence_splitting import SilenceSplittingStep
from app.pipeline.steps.audio_splitting import AudioSplittingStep

__all__ = [
    'AudioResamplingStep',
    'SilenceDetectionStep',
    'ChunkMergingStep',
    'ChunkTranscriptionStep',
    'DuplicateRemovalStep',
    'TranscriptionCombiningStep',
    'VerseMatchingStep',
    'TranscriptionAlignmentStep',
    'TimestampCalculationStep',
    'SilenceSplittingStep',
    'AudioSplittingStep',
]
