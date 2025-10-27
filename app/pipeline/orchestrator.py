"""
Pipeline Orchestrator - Factory and configuration for the transcription pipeline.

This module provides a high-level interface for creating and executing
the complete transcription pipeline.
"""

from typing import Optional, List, Any
import logging
import os

from app.pipeline.base import Pipeline, PipelineContext
from app.pipeline.steps import (
    AudioResamplingStep,
    SilenceDetectionStep,
    ChunkMergingStep,
    ChunkTranscriptionStep,
    DuplicateRemovalStep,
    TranscriptionCombiningStep,
    VerseMatchingStep,
    TranscriptionAlignmentStep,
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
    def _get_config_value(
        key: str,
        config: dict,
        default: Any,
        value_type: type = str
    ) -> Any:
        """
        Get configuration value with fallback chain.
        
        Priority (highest to lowest):
        1. Passed config parameter
        2. Environment variable (PIPELINE_{KEY})
        3. Default value
        
        Args:
            key: Configuration key name
            config: Configuration dictionary passed to function
            default: Default value if not found in config or env
            value_type: Type to cast the value to (int, float, str, bool)
            
        Returns:
            Configuration value with proper type
        """
        # Priority 1: Check passed config
        if key in config:
            return config[key]
        
        # Priority 2: Check environment variable
        env_key = f"PIPELINE_{key.upper()}"
        env_value = os.getenv(env_key)
        
        if env_value is not None:
            # Cast to appropriate type
            try:
                if value_type == bool:
                    return env_value.lower() in ('true', '1', 'yes', 'on')
                elif value_type == int:
                    return int(env_value)
                elif value_type == float:
                    return float(env_value)
                else:
                    return env_value
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse env var {env_key}={env_value} as {value_type.__name__}: {e}")
                return default
        
        # Priority 3: Use default
        return default
    
    @staticmethod
    def create_full_pipeline(
        model,
        processor,
        device,
        config: Optional[dict] = None
    ) -> Pipeline:
        """
        Create the complete transcription pipeline with all steps.
        
        Configuration Priority (highest to lowest):
        1. config parameter passed to this function
        2. Environment variables (PIPELINE_*)
        3. Default values
        
        Args:
            model: Whisper model instance
            processor: Whisper processor instance
            device: Device to run model on (cuda/cpu)
            config: Optional configuration dictionary for step parameters
            
        Returns:
            Configured Pipeline instance
            
        Environment Variables:
            PIPELINE_TARGET_SAMPLE_RATE - Target sample rate (default: 16000)
            PIPELINE_MIN_SILENCE_LEN - Min silence length in ms (default: 500)
            PIPELINE_SILENCE_THRESH - Silence threshold in dBFS (default: -40)
            PIPELINE_KEEP_SILENCE - Silence padding in ms (default: 200)
            PIPELINE_MIN_CHUNK_DURATION - Min chunk duration in seconds (default: 3.0)
            PIPELINE_MIN_SILENCE_GAP - Min silence gap in seconds (default: 0.5)
        """
        config = config or {}
        
        logger.info("Creating full transcription pipeline")
        
        # Get configuration values with fallback chain
        get_config = lambda key, default, vtype=str: PipelineOrchestrator._get_config_value(
            key, config, default, vtype
        )
        
        pipeline = Pipeline(name="QuranTranscriptionPipeline")
        
        # Step 1: Audio Resampling
        target_sample_rate = get_config('target_sample_rate', 16000, int)
        pipeline.add_step(AudioResamplingStep(
            target_sample_rate=target_sample_rate
        ))
        logger.debug(f"AudioResamplingStep: target_sample_rate={target_sample_rate}")
        
        # Step 2: Silence Detection
        min_silence_len = get_config('min_silence_len', 500, int)
        silence_thresh = get_config('silence_thresh', -40, int)
        keep_silence = get_config('keep_silence', 200, int)
        pipeline.add_step(SilenceDetectionStep(
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=keep_silence
        ))
        logger.debug(f"SilenceDetectionStep: min_silence_len={min_silence_len}, "
                    f"silence_thresh={silence_thresh}, keep_silence={keep_silence}")
        
        # Step 3: Chunk Merging
        min_chunk_duration = get_config('min_chunk_duration', 3.0, float)
        min_silence_gap = get_config('min_silence_gap', 0.5, float)
        pipeline.add_step(ChunkMergingStep(
            min_chunk_duration=min_chunk_duration,
            min_silence_gap=min_silence_gap
        ))
        logger.debug(f"ChunkMergingStep: min_chunk_duration={min_chunk_duration}, "
                    f"min_silence_gap={min_silence_gap}")
        
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
        
        # Step 7.5: Transcription Alignment (Word-level timestamps)
        alignment_method = get_config('alignment_method', 'wav2vec2', str)
        alignment_language = get_config('alignment_language', 'ar', str)
        pipeline.add_step(TranscriptionAlignmentStep(
            alignment_method=alignment_method,
            language=alignment_language
        ))
        logger.debug(f"TranscriptionAlignmentStep: alignment_method={alignment_method}, language={alignment_language}")
        
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
        Uses same configuration priority as create_full_pipeline.
        
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
        
        # Get configuration values with fallback chain
        get_config = lambda key, default, vtype=str: PipelineOrchestrator._get_config_value(
            key, config, default, vtype
        )
        
        pipeline = Pipeline(name="PartialPipeline")
        
        step_map = {
            'AudioResamplingStep': lambda: AudioResamplingStep(
                target_sample_rate=get_config('target_sample_rate', 16000, int)
            ),
            'SilenceDetectionStep': lambda: SilenceDetectionStep(
                min_silence_len=get_config('min_silence_len', 500, int),
                silence_thresh=get_config('silence_thresh', -40, int),
                keep_silence=get_config('keep_silence', 200, int)
            ),
            'ChunkMergingStep': lambda: ChunkMergingStep(
                min_chunk_duration=get_config('min_chunk_duration', 3.0, float),
                min_silence_gap=get_config('min_silence_gap', 0.5, float)
            ),
            'ChunkTranscriptionStep': lambda: ChunkTranscriptionStep(
                model=model,
                processor=processor,
                device=device
            ),
            'DuplicateRemovalStep': lambda: DuplicateRemovalStep(),
            'TranscriptionCombiningStep': lambda: TranscriptionCombiningStep(),
            'VerseMatchingStep': lambda: VerseMatchingStep(),
            'TranscriptionAlignmentStep': lambda: TranscriptionAlignmentStep(
                alignment_method=get_config('alignment_method', 'wav2vec2', str),
                language=get_config('alignment_language', 'ar', str)
            ),
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
