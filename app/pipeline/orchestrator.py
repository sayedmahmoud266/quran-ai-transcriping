"""
Pipeline Orchestrator - Factory and configuration for the transcription pipeline.

This module provides a high-level interface for creating and executing
the complete transcription pipeline.
"""

from typing import Optional, List
import logging

from app.pipeline.base import Pipeline, PipelineContext
from app.pipeline.steps import (
    AudioResamplingStep,
    SilenceDetectionStep,
    ChunkMergingStep,
    ChunkTranscriptionStep,
    DuplicateRemovalStep,
    TranscriptionCombiningStep,
    VerseMatchingStep,
    TimestampCalculationStep,
    SilenceSplittingStep,
    AudioSplittingStep,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """
    Orchestrator for creating and managing transcription pipelines.
    
    This class provides factory methods for creating pre-configured pipelines
    and utilities for pipeline execution and monitoring.
    """
    
    @staticmethod
    def create_full_pipeline(
        model,
        processor,
        device,
        config: Optional[dict] = None
    ) -> Pipeline:
        """
        Create the complete transcription pipeline with all steps.
        
        Args:
            model: Whisper model instance
            processor: Whisper processor instance
            device: Device to run model on (cuda/cpu)
            config: Optional configuration dictionary for step parameters
            
        Returns:
            Configured Pipeline instance
        """
        config = config or {}
        
        logger.info("Creating full transcription pipeline")
        
        pipeline = Pipeline(name="QuranTranscriptionPipeline")
        
        # Step 1: Audio Resampling
        pipeline.add_step(AudioResamplingStep(
            target_sample_rate=config.get('target_sample_rate', 16000)
        ))
        
        # Step 2: Silence Detection
        pipeline.add_step(SilenceDetectionStep(
            min_silence_len=config.get('min_silence_len', 500),
            silence_thresh=config.get('silence_thresh', -40),
            keep_silence=config.get('keep_silence', 200)
        ))
        
        # Step 3: Chunk Merging
        pipeline.add_step(ChunkMergingStep(
            min_chunk_duration=config.get('min_chunk_duration', 3.0),
            min_silence_gap=config.get('min_silence_gap', 0.5)
        ))
        
        # Step 4: Chunk Transcription
        pipeline.add_step(ChunkTranscriptionStep(
            model=model,
            processor=processor,
            device=device
        ))
        
        # Step 5: Duplicate Removal
        pipeline.add_step(DuplicateRemovalStep())
        
        # Step 6: Transcription Combining
        pipeline.add_step(TranscriptionCombiningStep())
        
        # Step 7: Verse Matching
        pipeline.add_step(VerseMatchingStep())
        
        # Step 8: Timestamp Calculation
        pipeline.add_step(TimestampCalculationStep())
        
        # Step 9: Silence Splitting
        pipeline.add_step(SilenceSplittingStep())
        
        # Step 10: Audio Splitting (preparation)
        pipeline.add_step(AudioSplittingStep())
        
        logger.info(f"Pipeline created with {len(pipeline.steps)} steps")
        
        return pipeline
    
    @staticmethod
    def create_partial_pipeline(
        step_names: List[str],
        model=None,
        processor=None,
        device=None,
        config: Optional[dict] = None
    ) -> Pipeline:
        """
        Create a partial pipeline with only specified steps.
        
        Useful for testing or running only part of the pipeline.
        
        Args:
            step_names: List of step names to include
            model: Whisper model (required for transcription step)
            processor: Whisper processor (required for transcription step)
            device: Device (required for transcription step)
            config: Optional configuration dictionary
            
        Returns:
            Configured Pipeline instance
        """
        config = config or {}
        
        pipeline = Pipeline(name="PartialPipeline")
        
        step_map = {
            'AudioResamplingStep': lambda: AudioResamplingStep(
                target_sample_rate=config.get('target_sample_rate', 16000)
            ),
            'SilenceDetectionStep': lambda: SilenceDetectionStep(
                min_silence_len=config.get('min_silence_len', 500),
                silence_thresh=config.get('silence_thresh', -40),
                keep_silence=config.get('keep_silence', 200)
            ),
            'ChunkMergingStep': lambda: ChunkMergingStep(
                min_chunk_duration=config.get('min_chunk_duration', 3.0),
                min_silence_gap=config.get('min_silence_gap', 0.5)
            ),
            'ChunkTranscriptionStep': lambda: ChunkTranscriptionStep(
                model=model,
                processor=processor,
                device=device
            ),
            'DuplicateRemovalStep': lambda: DuplicateRemovalStep(),
            'TranscriptionCombiningStep': lambda: TranscriptionCombiningStep(),
            'VerseMatchingStep': lambda: VerseMatchingStep(),
            'TimestampCalculationStep': lambda: TimestampCalculationStep(),
            'SilenceSplittingStep': lambda: SilenceSplittingStep(),
            'AudioSplittingStep': lambda: AudioSplittingStep(),
        }
        
        for step_name in step_names:
            if step_name in step_map:
                pipeline.add_step(step_map[step_name]())
            else:
                logger.warning(f"Unknown step name: {step_name}")
        
        logger.info(f"Partial pipeline created with {len(pipeline.steps)} steps")
        
        return pipeline
    
    @staticmethod
    def execute_pipeline(
        pipeline: Pipeline,
        audio_array,
        sample_rate: int,
        debug_recorder=None
    ) -> PipelineContext:
        """
        Execute a pipeline with the given audio data.
        
        Args:
            pipeline: Pipeline instance to execute
            audio_array: Audio data as numpy array
            sample_rate: Audio sample rate
            debug_recorder: Optional debug recorder for saving intermediate results
            
        Returns:
            Final PipelineContext with results
        """
        # Create initial context
        context = PipelineContext(
            audio_array=audio_array,
            sample_rate=sample_rate
        )
        
        # Set debug recorder if provided
        if debug_recorder:
            context.set('debug_recorder', debug_recorder)
        
        # Execute pipeline
        context = pipeline.execute(context)
        
        return context
    
    @staticmethod
    def get_pipeline_summary(context: PipelineContext) -> dict:
        """
        Get a summary of pipeline execution results.
        
        Args:
            context: Final pipeline context
            
        Returns:
            Dictionary with execution summary
        """
        summary = {
            'steps_executed': len(context.step_results),
            'total_duration': sum(
                result['duration'] for result in context.step_results.values()
            ),
            'steps': []
        }
        
        for step_name, result in context.step_results.items():
            summary['steps'].append({
                'name': step_name,
                'status': result['status'],
                'duration': result['duration']
            })
        
        return summary
    
    @staticmethod
    def validate_pipeline_config(config: dict) -> bool:
        """
        Validate pipeline configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if valid, False otherwise
        """
        # Add validation logic here
        return True
