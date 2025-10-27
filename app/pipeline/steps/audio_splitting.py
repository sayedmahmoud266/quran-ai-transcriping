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
        
        Now that we extract precise timings from word alignments for multi-ayah chunks,
        each ayah should get its own audio file with accurate timestamps.
        
        No merging needed - all verses have proper timing from word-level alignment.
        """
        # Get verse_slices_timestamps from context
        verse_slices_timestamps = context.verse_slices_timestamps
        
        self.logger.info(f"Processing {len(verse_slices_timestamps)} verses for audio splitting...")
        
        # Simply copy all verses - they all have proper timing now
        verse_details = []
        
        for verse in verse_slices_timestamps:
            verse_copy = verse.copy()
            
            # Log if this was extracted from multi-ayah chunk
            if verse.get('extracted_from_multi_ayah', False):
                self.logger.info(
                    f"Ayah {verse['surah_number']}:{verse['ayah_number']} "
                    f"extracted from multi-ayah chunk with word alignments "
                    f"({verse['start_time']:.2f}s - {verse['end_time']:.2f}s)"
                )
            
            verse_details.append(verse_copy)
        
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
