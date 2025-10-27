"""
Silence Splitting Step - Step 9 of the pipeline.

Splits silence between consecutive verses.
"""

from app.pipeline.base import PipelineStep, PipelineContext


class SilenceSplittingStep(PipelineStep):
    """
    Split silence between consecutive verses.
    
    Input (from context):
        - verse_details: Verses with timestamps
    
    Output (to context):
        - verse_details: Verses with adjusted timestamps
    """
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that verse_slices_timestamps are present."""
        if not hasattr(context, 'verse_slices_timestamps') or not context.verse_slices_timestamps:
            self.logger.error("No verse_slices_timestamps in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Split silence between verses.
        
        Calculates silence gaps between consecutive verses and splits them in half,
        adding each half to the end of the previous verse and start of the next verse.
        
        Note: Verses with 0 duration (from chunk_reuse) are skipped in gap calculation.
        """
        verse_slices_timestamps = context.verse_slices_timestamps
        
        self.logger.info(f"Splitting silence for {len(verse_slices_timestamps)} verses...")
        
        # Process each verse and calculate normalized timestamps
        for i, verse in enumerate(verse_slices_timestamps):
            start_time = verse['start_time']
            end_time = verse['end_time']
            duration = end_time - start_time
            
            # Skip verses with 0 duration (reused chunks from multi-ayah case)
            if duration <= 0:
                self.logger.debug(
                    f"Skipping silence splitting for verse {verse['surah_number']}:{verse['ayah_number']} "
                    f"(0 duration - chunk reuse case)"
                )
                verse['prev_gap_duration'] = 0.0
                verse['normalized_start_time'] = 0.0
                verse['normalized_end_time'] = 0.0
                verse['normalized_duration'] = 0.0
                continue
            
            # Calculate gap with previous verse
            if i > 0:
                prev_verse = verse_slices_timestamps[i - 1]
                prev_end_time = prev_verse['end_time']
                
                # Calculate silence gap duration
                gap_duration = start_time - prev_end_time
                
                # Split the gap in half
                half_gap = gap_duration / 2.0
                
                # Adjust start time by subtracting half the gap
                normalized_start_time = start_time - half_gap
                
                # Also update the previous verse's normalized_end_time
                # (add the other half of the gap to its end)
                prev_verse['normalized_end_time'] = prev_end_time + half_gap
                prev_verse['normalized_duration'] = prev_verse['normalized_end_time'] - prev_verse['normalized_start_time']
            else:
                # First verse: no previous gap, start from original start_time
                gap_duration = 0.0
                normalized_start_time = start_time
            
            # Store gap duration and normalized start time
            verse['prev_gap_duration'] = gap_duration
            verse['normalized_start_time'] = normalized_start_time
            
            # For now, set normalized_end_time to original end_time
            # It will be updated when processing the next verse
            verse['normalized_end_time'] = end_time
            verse['normalized_duration'] = verse['normalized_end_time'] - verse['normalized_start_time']
        
        # Handle the last verse: extend to original end_time (no next verse to split with)
        if verse_slices_timestamps:
            last_verse = verse_slices_timestamps[-1]
            # Last verse keeps its original end_time as normalized_end_time
            last_verse['normalized_duration'] = last_verse['normalized_end_time'] - last_verse['normalized_start_time']
        
        # Save back to context
        context.verse_slices_timestamps = verse_slices_timestamps
        
        self.logger.info(f"Completed silence splitting for {len(verse_slices_timestamps)} verses")
        
        # Calculate statistics
        total_gap_duration = sum(v.get('prev_gap_duration', 0) for v in verse_slices_timestamps)
        avg_gap_duration = total_gap_duration / len(verse_slices_timestamps) if verse_slices_timestamps else 0
        
        context.add_debug_info(self.name, {
            'total_verses': len(verse_slices_timestamps),
            'total_gap_duration': total_gap_duration,
            'avg_gap_duration': avg_gap_duration,
            'verse_slices_timestamps': verse_slices_timestamps
        })
        
        return context
