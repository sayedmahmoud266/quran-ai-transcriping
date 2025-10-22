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
        Calculate timestamps.
        
        Remaps matched_chunk_verses from chunk-centric to verse-centric structure.
        Ensures chunks are consecutive and validates overlapping/consecutive transcriptions.
        """
        matched_chunk_verses = context.matched_chunk_verses
        
        self.logger.info(f"Calculating timestamps for chunks with matched verses...")
        
        # Remap the matched_chunk_verses from being a list of chunks, and each chunk contains matched_ayahs
        # into a list of verses, and each verse contains matched_chunks
        
        # Create a dictionary to group chunks by verse
        verse_to_chunks = {}
        
        for chunk_data in matched_chunk_verses:
            # Get all matched ayahs for this chunk
            matched_ayahs = chunk_data.get('matched_ayahs', [])
            
            for ayah in matched_ayahs:
                # Create a unique key for each verse (surah:ayah)
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
                
                # Add chunk info to this verse
                verse_to_chunks[verse_key]['chunks'].append({
                    'chunk_index': chunk_data.get('chunk_index'),
                    'chunk_start_time': chunk_data.get('chunk_start_time'),
                    'chunk_end_time': chunk_data.get('chunk_end_time'),
                    'chunk_normalized_text': chunk_data.get('chunk_normalized_text', ''),
                    'similarity': ayah.get('similarity', chunk_data.get('similarity'))
                })
        
        # Convert to list and process each verse
        verse_slices_timestamps = []
        last_chunk_index = -1
        
        # Get sorted list of verse keys to access prev/next verses
        sorted_verse_keys = sorted(verse_to_chunks.keys())
        
        for idx, verse_key in enumerate(sorted_verse_keys):
            verse_data = verse_to_chunks[verse_key]
            chunks = verse_data['chunks']
            
            if not chunks:
                continue
            
            # Sort chunks by chunk_index
            chunks.sort(key=lambda c: c['chunk_index'])
            
            # Get ayah sequence context (prev, current, next)
            current_ayah_text = verse_data['text_normalized']
            prev_ayah_text = None
            next_ayah_text = None
            
            if idx > 0:
                prev_verse_key = sorted_verse_keys[idx - 1]
                prev_ayah_text = verse_to_chunks[prev_verse_key]['text_normalized']
            
            if idx < len(sorted_verse_keys) - 1:
                next_verse_key = sorted_verse_keys[idx + 1]
                next_ayah_text = verse_to_chunks[next_verse_key]['text_normalized']
            
            # Filter chunks to keep only consecutive ones starting after the last verse's chunks
            filtered_chunks = []
            
            for chunk in chunks:
                chunk_idx = chunk['chunk_index']
                
                # If this is the first chunk for this verse
                if not filtered_chunks:
                    # Only accept if it's chronologically after the previous verse's chunks
                    if chunk_idx > last_chunk_index:
                        filtered_chunks.append(chunk)
                else:
                    # Check if this chunk is consecutive to the last filtered chunk
                    if chunk_idx == filtered_chunks[-1]['chunk_index'] + 1:
                        # Validate overlapping or consecutive transcription parts
                        prev_chunk_text = filtered_chunks[-1]['chunk_normalized_text']
                        curr_chunk_text = chunk['chunk_normalized_text']
                        
                        # Check if chunks are consecutive in the context of the ayah sequence
                        if self._are_chunks_consecutive(
                            prev_chunk_text, 
                            curr_chunk_text,
                            prev_ayah_text,
                            current_ayah_text,
                            next_ayah_text
                        ):
                            filtered_chunks.append(chunk)
                        else:
                            self.logger.debug(
                                f"Verse {verse_key}: Skipping non-consecutive text in chunk {chunk_idx}"
                            )
                            break
                    else:
                        # Not consecutive, stop here
                        break
            
            if not filtered_chunks:
                self.logger.warning(f"Verse {verse_key}: No valid consecutive chunks found")
                continue
            
            # Update last_chunk_index
            last_chunk_index = filtered_chunks[-1]['chunk_index']
            
            # Get boundaries: start of first chunk, end of last chunk
            start_time = filtered_chunks[0]['chunk_start_time']
            end_time = filtered_chunks[-1]['chunk_end_time']
            duration = end_time - start_time
            
            verse_slices_timestamps.append({
                'surah_number': verse_data['surah_number'],
                'ayah_number': verse_data['ayah_number'],
                'text': verse_data['text'],
                'text_normalized': verse_data['text_normalized'],
                'is_basmalah': verse_data['is_basmalah'],
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'chunks': filtered_chunks,
                'num_chunks': len(filtered_chunks)
            })
        
        context.verse_slices_timestamps = verse_slices_timestamps
        
        self.logger.info(f"Calculated timestamps for {len(verse_slices_timestamps)} verses")
        
        context.add_debug_info(self.name, {
            'total_verses': len(verse_slices_timestamps),
            'verse_slices_timestamps': verse_slices_timestamps
        })
        
        return context
    
    def _are_chunks_consecutive(
        self, 
        prev_chunk_text: str, 
        curr_chunk_text: str,
        prev_ayah_text: str,
        current_ayah_text: str,
        next_ayah_text: str
    ) -> bool:
        """
        Check if two chunks are consecutive by verifying they appear in sequence
        within the ayah context.
        
        Two chunks are consecutive if:
        1. They have overlapping words (indicating same content boundary)
        2. OR they appear sequentially in the ayah sequence (prev + current + next)
        
        Args:
            prev_chunk_text: Previous chunk's normalized text
            curr_chunk_text: Current chunk's normalized text
            prev_ayah_text: Previous ayah's normalized text (can be None)
            current_ayah_text: Current ayah's normalized text
            next_ayah_text: Next ayah's normalized text (can be None)
            
        Returns:
            True if chunks are consecutive or overlapping, False otherwise
        """
        if not prev_chunk_text or not curr_chunk_text:
            return False
        
        prev_words = prev_chunk_text.split()
        curr_words = curr_chunk_text.split()
        
        if not prev_words or not curr_words:
            return False
        
        # Check for exact overlap: last N words of prev match first N words of curr
        max_overlap = min(len(prev_words), len(curr_words), 10)
        
        for overlap in range(max_overlap, 0, -1):
            if prev_words[-overlap:] == curr_words[:overlap]:
                return True
        
        # Build the ayah sequence context
        ayah_sequence_parts = []
        if prev_ayah_text:
            ayah_sequence_parts.append(prev_ayah_text)
        if current_ayah_text:
            ayah_sequence_parts.append(current_ayah_text)
        if next_ayah_text:
            ayah_sequence_parts.append(next_ayah_text)
        
        if not ayah_sequence_parts:
            return False
        
        # Combine into full sequence
        full_ayah_sequence = ' '.join(ayah_sequence_parts)
        
        # Find positions of prev_chunk and curr_chunk in the sequence
        from rapidfuzz import fuzz
        
        # Use fuzzy search to find where each chunk appears in the sequence
        # We'll check if prev_chunk appears before curr_chunk in the sequence
        
        # Find the best match position for prev_chunk
        prev_chunk_pos = full_ayah_sequence.find(prev_chunk_text)
        if prev_chunk_pos == -1:
            # Try fuzzy matching for prev chunk
            # Check if prev chunk appears in the sequence with high similarity
            words_in_sequence = full_ayah_sequence.split()
            prev_chunk_found = False
            prev_end_pos = 0
            
            for i in range(len(words_in_sequence) - len(prev_words) + 1):
                window = ' '.join(words_in_sequence[i:i + len(prev_words)])
                if fuzz.ratio(prev_chunk_text, window) >= 85:
                    prev_chunk_found = True
                    prev_end_pos = len(' '.join(words_in_sequence[:i + len(prev_words)]))
                    break
            
            if not prev_chunk_found:
                return False
        else:
            prev_end_pos = prev_chunk_pos + len(prev_chunk_text)
        
        # Find the best match position for curr_chunk
        curr_chunk_pos = full_ayah_sequence.find(curr_chunk_text, prev_end_pos)
        if curr_chunk_pos == -1:
            # Try fuzzy matching for curr chunk starting after prev chunk
            words_in_sequence = full_ayah_sequence.split()
            # Calculate word offset for prev_end_pos
            words_before = full_ayah_sequence[:prev_end_pos].split()
            start_word_idx = len(words_before)
            
            for i in range(start_word_idx, len(words_in_sequence) - len(curr_words) + 1):
                window = ' '.join(words_in_sequence[i:i + len(curr_words)])
                if fuzz.ratio(curr_chunk_text, window) >= 85:
                    # Found curr chunk after prev chunk in sequence
                    return True
            
            return False
        
        # If we found both chunks and curr comes after prev, they're consecutive
        return curr_chunk_pos >= prev_end_pos
