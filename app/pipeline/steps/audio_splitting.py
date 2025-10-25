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
        
        Special handling for multi-ayah chunks:
        - Verses with 0 duration (chunk_reuse) are merged into the first verse's audio file
        - Only the first verse gets an actual audio file
        - Subsequent verses are marked as references to the first verse
        """
        # Get verse_slices_timestamps from context
        verse_slices_timestamps = context.verse_slices_timestamps
        
        self.logger.info(f"Processing {len(verse_slices_timestamps)} verses for audio splitting...")
        
        # Group verses by chunk_index to identify multi-ayah cases
        verse_details = []
        i = 0
        
        while i < len(verse_slices_timestamps):
            verse = verse_slices_timestamps[i]
            duration = verse.get('normalized_duration', verse.get('duration', 0))
            
            # Check if this is a multi-ayah chunk (0 duration indicates chunk_reuse)
            if duration <= 0 and i > 0:
                # This verse reuses a chunk - merge with previous verse
                prev_verse = verse_details[-1]
                
                # Add this ayah to the previous verse's ayah list
                if 'multi_ayahs' not in prev_verse:
                    # Convert previous verse to multi-ayah format
                    prev_verse['multi_ayahs'] = [{
                        'surah_number': prev_verse['surah_number'],
                        'ayah_number': prev_verse['ayah_number'],
                        'text': prev_verse['text'],
                        'text_normalized': prev_verse['text_normalized'],
                        'is_basmalah': prev_verse.get('is_basmalah', False)
                    }]
                
                # Add current ayah to the list
                prev_verse['multi_ayahs'].append({
                    'surah_number': verse['surah_number'],
                    'ayah_number': verse['ayah_number'],
                    'text': verse['text'],
                    'text_normalized': verse['text_normalized'],
                    'is_basmalah': verse.get('is_basmalah', False)
                })
                
                self.logger.info(
                    f"Merged ayah {verse['surah_number']}:{verse['ayah_number']} "
                    f"into multi-ayah file (total: {len(prev_verse['multi_ayahs'])} ayahs)"
                )
            else:
                # Normal verse or first verse in multi-ayah chunk
                verse_details.append(verse.copy())
            
            i += 1
        
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
