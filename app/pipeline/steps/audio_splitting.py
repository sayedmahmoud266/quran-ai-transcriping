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
        """Validate that verse_slices_timestamps are present."""
        if not hasattr(context, 'verse_slices_timestamps') or not context.verse_slices_timestamps:
            self.logger.error("No verse_slices_timestamps in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Copy verse_slices_timestamps to verse_details and mark as ready for splitting.
        """
        # Get verse_slices_timestamps from context
        verse_slices_timestamps = context.verse_slices_timestamps
        
        self.logger.info(f"Copying {len(verse_slices_timestamps)} verses to verse_details...")
        
        # Copy verse_slices_timestamps to verse_details
        # This creates a deep copy so modifications don't affect the original
        verse_details = []
        for verse in verse_slices_timestamps:
            verse_details.append(verse.copy())
        
        # Set verse_details in context
        context.verse_details = verse_details
        
        # Mark metadata as ready for splitting
        context.set('ready_for_splitting', True)
        
        self.logger.info(f"Prepared {len(verse_details)} verses for audio splitting")
        
        context.add_debug_info(self.name, {
            'total_verses': len(verse_details),
            'ready': True,
            'verse_details': verse_details
        })
        
        return context
