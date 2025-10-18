"""
Audio Splitting Step - Step 10 of the pipeline.

Splits audio into individual verse files (handled externally).
"""

from app.pipeline.base import PipelineStep, PipelineContext


class AudioSplittingStep(PipelineStep):
    """
    Prepare data for audio splitting.
    
    Note: Actual audio splitting is handled by audio_splitter module.
    This step just validates the data is ready.
    
    Input (from context):
        - verse_details: Verses with timestamps
    
    Output (to context):
        - metadata['ready_for_splitting']: True
    """
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that verse details are present."""
        if not context.verse_details:
            self.logger.error("No verse details in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Mark data as ready for audio splitting.
        """
        verse_details = context.verse_details
        
        self.logger.info(f"Prepared {len(verse_details)} verses for audio splitting")
        
        context.set('ready_for_splitting', True)
        
        context.add_debug_info(self.name, {
            'total_verses': len(verse_details),
            'ready': True
        })
        
        return context
