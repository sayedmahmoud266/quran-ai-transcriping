"""
Timestamp Calculation Step - Step 8 of the pipeline.

Calculates accurate timestamps for each verse.
"""

from app.pipeline.base import PipelineStep, PipelineContext


class TimestampCalculationStep(PipelineStep):
    """
    Calculate accurate timestamps for verses.
    
    Input (from context):
        - matched_verses: List of matched verses
        - chunks: Chunk data with timestamps
    
    Output (to context):
        - verse_details: Verses with accurate timestamps
    """
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that matched verses are present."""
        if not context.matched_verses:
            self.logger.error("No matched verses in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Calculate verse timestamps by reorganizing chunk-to-verse mappings.
        
        Logic:
        1. Transform data structure from chunk-centric to verse-centric
        2. Extract timing boundaries (start/end) from the chunks assigned to each verse
        
        Input: matched_chunk_verses (list of chunks, each containing matched_ayahs)
        Output: verse_slices_timestamps (list of verses, each containing chunks and timing)
        """
        matched_chunk_verses = context.matched_chunk_verses
        
        self.logger.info(f"Calculating timestamps from {len(matched_chunk_verses)} matched chunks...")
        
        # Step 1: Reorganize from chunk-centric to verse-centric structure
        # Transform: [chunks with ayahs] → [ayahs with chunks]
        verse_to_chunks = {}
        
        for chunk_data in matched_chunk_verses:
            matched_ayahs = chunk_data.get('matched_ayahs', [])
            chunk_reuse = chunk_data.get('chunk_reuse', False)
            
            # Skip reused chunks - they have 0 timing and shouldn't be counted twice
            if chunk_reuse:
                self.logger.debug(
                    f"Skipping reused chunk {chunk_data.get('chunk_index')} "
                    f"for ayah {matched_ayahs[0]['surah_number']}:{matched_ayahs[0]['ayah_number']}"
                )
                continue
            
            for ayah in matched_ayahs:
                # Create unique verse key (surah:ayah)
                verse_key = (ayah['surah_number'], ayah['ayah_number'])
                
                # Initialize verse entry if not exists
                if verse_key not in verse_to_chunks:
                    verse_to_chunks[verse_key] = {
                        'surah_number': ayah['surah_number'],
                        'ayah_number': ayah['ayah_number'],
                        'text': ayah['text'],
                        'text_normalized': ayah['text_normalized'],
                        'is_basmalah': ayah['is_basmalah'],
                        'chunks': []
                    }
                
                # Add chunk to this verse
                verse_to_chunks[verse_key]['chunks'].append({
                    'chunk_index': chunk_data.get('chunk_index'),
                    'chunk_start_time': chunk_data.get('chunk_start_time'),
                    'chunk_end_time': chunk_data.get('chunk_end_time'),
                    'chunk_normalized_text': chunk_data.get('chunk_normalized_text', ''),
                    'similarity': ayah.get('similarity', chunk_data.get('similarity'))
                })
        
        # Step 2: Process each verse and extract timing boundaries
        verse_slices_timestamps = []
        
        for verse_key in sorted(verse_to_chunks.keys()):
            verse_data = verse_to_chunks[verse_key]
            chunks = verse_data['chunks']
            
            if not chunks:
                self.logger.warning(f"Verse {verse_key}: No chunks found")
                continue
            
            # Sort chunks by index to ensure correct order
            chunks.sort(key=lambda c: c['chunk_index'])
            
            # Extract timing boundaries from chunks
            start_time = chunks[0]['chunk_start_time']  # Start of first chunk
            end_time = chunks[-1]['chunk_end_time']      # End of last chunk
            duration = end_time - start_time
            
            # Create verse entry with timing information
            verse_slices_timestamps.append({
                'surah_number': verse_data['surah_number'],
                'ayah_number': verse_data['ayah_number'],
                'text': verse_data['text'],
                'text_normalized': verse_data['text_normalized'],
                'is_basmalah': verse_data['is_basmalah'],
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'chunks': chunks,
                'num_chunks': len(chunks)
            })
            
            self.logger.debug(
                f"Surah {verse_data['surah_number']}:Ayah {verse_data['ayah_number']}: "
                f"{len(chunks)} chunk(s), {start_time:.2f}s - {end_time:.2f}s ({duration:.2f}s)"
            )
        
        context.verse_slices_timestamps = verse_slices_timestamps
        
        self.logger.info(f"Calculated timestamps for {len(verse_slices_timestamps)} verses")
        
        context.add_debug_info(self.name, {
            'total_verses': len(verse_slices_timestamps),
            'verse_slices_timestamps': verse_slices_timestamps
        })
        
        return context
