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
        
        # Step 0: Pre-process chunks - split multi-ayah chunks into individual ayah chunks
        # Group chunks by chunk_index to identify multi-ayah cases
        chunks_by_index = {}
        for chunk_data in matched_chunk_verses:
            chunk_index = chunk_data.get('chunk_index')
            if chunk_index not in chunks_by_index:
                chunks_by_index[chunk_index] = []
            chunks_by_index[chunk_index].append(chunk_data)
        
        updated_matched_chunk_verses = []
        
        for chunk_index, chunk_group in chunks_by_index.items():
            # Check if this is a multi-ayah chunk (has reused chunks)
            is_multi_ayah_chunk = len(chunk_group) > 1
            
            if not is_multi_ayah_chunk:
                # Single ayah chunk - add as is
                updated_matched_chunk_verses.append(chunk_group[0])
                self.logger.debug(
                    f"Chunk {chunk_index}: Single ayah, keeping as is"
                )
            else:
                # Multi-ayah chunk - find the primary chunk and split
                primary_chunk = None
                all_ayahs = []
                
                for chunk_data in chunk_group:
                    chunk_reuse = chunk_data.get('chunk_reuse', False)
                    matched_ayahs = chunk_data.get('matched_ayahs', [])
                    
                    if not chunk_reuse:
                        primary_chunk = chunk_data
                    
                    # Collect all ayahs (each chunk_data has 1 ayah in matched_ayahs)
                    if matched_ayahs:
                        all_ayahs.append(matched_ayahs[0])
                
                if not primary_chunk:
                    self.logger.warning(
                        f"Chunk {chunk_index}: No primary chunk found (all are reused), skipping"
                    )
                    continue
                
                self.logger.info(
                    f"Chunk {chunk_index}: Multi-ayah chunk with {len(all_ayahs)} ayahs, splitting..."
                )
                
                if 'word_alignments' not in primary_chunk:
                    self.logger.warning(
                        f"Multi-ayah chunk {chunk_index} missing word_alignments, skipping"
                    )
                    continue
                
                # Split this chunk into individual ayah chunks
                for ayah in all_ayahs:
                    # Extract timing for this specific ayah from word alignments
                    ayah_timing = self._extract_ayah_timing_from_words(
                        ayah['text_normalized'],
                        primary_chunk.get('chunk_normalized_text', ''),
                        primary_chunk['word_alignments']
                    )
                    
                    if not ayah_timing:
                        self.logger.warning(
                            f"Could not extract timing for ayah {ayah['surah_number']}:{ayah['ayah_number']} "
                            f"from multi-ayah chunk {chunk_index}"
                        )
                        continue
                    
                    # Create a new chunk for this ayah
                    new_chunk = {
                        'chunk_index': chunk_index,
                        'chunk_start_time': ayah_timing['start_time'],
                        'chunk_end_time': ayah_timing['end_time'],
                        'chunk_text': ayah.get('text', ''),
                        'chunk_normalized_text': ayah['text_normalized'],
                        'matched_ayahs': [ayah],  # Only this ayah
                        'similarity': ayah.get('similarity', primary_chunk.get('similarity')),
                        'word_alignments': ayah_timing['word_alignments'],
                        'alignment_method': primary_chunk.get('alignment_method', 'unknown'),
                        'extracted_from_multi_ayah': True,
                        'chunk_reuse': False
                    }
                    
                    updated_matched_chunk_verses.append(new_chunk)
                    
                    self.logger.debug(
                        f"  Created new chunk for ayah {ayah['surah_number']}:{ayah['ayah_number']}: "
                        f"{ayah_timing['start_time']:.2f}s - {ayah_timing['end_time']:.2f}s "
                        f"({len(ayah_timing['word_alignments'])} words)"
                    )
        
        self.logger.info(
            f"Pre-processing complete: {len(matched_chunk_verses)} chunk entries → "
            f"{len(updated_matched_chunk_verses)} chunks (after splitting multi-ayah)"
        )
        
        # Step 1: Reorganize from chunk-centric to verse-centric structure
        # Transform: [chunks with ayahs] → [ayahs with chunks]
        verse_to_chunks = {}
        
        for chunk_data in updated_matched_chunk_verses:
            matched_ayahs = chunk_data.get('matched_ayahs', [])
            
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
                    
                    # Mark if extracted from multi-ayah
                    if chunk_data.get('extracted_from_multi_ayah', False):
                        verse_to_chunks[verse_key]['extracted_from_multi_ayah'] = True
                
                # Add chunk to this verse
                chunk_info = {
                    'chunk_index': chunk_data.get('chunk_index'),
                    'chunk_start_time': chunk_data.get('chunk_start_time'),
                    'chunk_end_time': chunk_data.get('chunk_end_time'),
                    'chunk_normalized_text': chunk_data.get('chunk_normalized_text', ''),
                    'similarity': ayah.get('similarity', chunk_data.get('similarity'))
                }
                
                # Include word alignments if available
                if 'word_alignments' in chunk_data:
                    chunk_info['word_alignments'] = chunk_data['word_alignments']
                    chunk_info['alignment_method'] = chunk_data.get('alignment_method', 'unknown')
                
                # Mark if extracted from multi-ayah
                if chunk_data.get('extracted_from_multi_ayah', False):
                    chunk_info['extracted_from_multi_ayah'] = True
                
                verse_to_chunks[verse_key]['chunks'].append(chunk_info)
        
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
            
            # Collect all word alignments from chunks
            all_word_alignments = []
            for chunk in chunks:
                if 'word_alignments' in chunk:
                    all_word_alignments.extend(chunk['word_alignments'])
            
            # Create verse entry with timing information
            verse_entry = {
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
            }
            
            # Add word alignments if available
            if all_word_alignments:
                verse_entry['word_alignments'] = all_word_alignments
                verse_entry['alignment_method'] = chunks[0].get('alignment_method', 'unknown')
            
            # Mark if this was extracted from multi-ayah chunk
            if verse_data.get('extracted_from_multi_ayah', False):
                verse_entry['extracted_from_multi_ayah'] = True
            
            verse_slices_timestamps.append(verse_entry)
            
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
    
    def _extract_ayah_timing_from_words(self, ayah_text, chunk_text, word_alignments):
        """
        Extract timing for a specific ayah from word alignments of the full chunk.
        
        Uses normalized text matching to find which words belong to this ayah.
        
        Args:
            ayah_text: Normalized text of the ayah to extract
            chunk_text: Normalized text of the full chunk
            word_alignments: List of word alignment dicts with 'word', 'start', 'end', 'confidence'
            
        Returns:
            Dict with 'start_time', 'end_time', 'word_alignments' or None
        """
        if not ayah_text or not word_alignments:
            return None
        
        # Split into words
        ayah_words = ayah_text.split()
        chunk_words = chunk_text.split()
        
        if not ayah_words or not chunk_words:
            return None
        
        # Find where this ayah's words appear in the chunk
        # Use simple substring matching on normalized text
        ayah_start_idx = None
        ayah_end_idx = None
        
        # Try to find the ayah words as a contiguous sequence in chunk words
        for i in range(len(chunk_words) - len(ayah_words) + 1):
            # Check if ayah words match chunk words starting at position i
            match = True
            for j, ayah_word in enumerate(ayah_words):
                if i + j >= len(chunk_words) or chunk_words[i + j] != ayah_word:
                    match = False
                    break
            
            if match:
                ayah_start_idx = i
                ayah_end_idx = i + len(ayah_words)
                break
        
        if ayah_start_idx is None:
            # Fallback: try fuzzy matching (allow some words to be different)
            self.logger.debug(f"Exact match failed for ayah, trying fuzzy match")
            ayah_start_idx, ayah_end_idx = self._fuzzy_find_ayah_words(
                ayah_words, chunk_words
            )
        
        if ayah_start_idx is None or ayah_end_idx is None:
            self.logger.warning(
                f"Could not locate ayah words in chunk. "
                f"Ayah: '{ayah_text[:50]}...', Chunk: '{chunk_text[:50]}...'"
            )
            return None
        
        # Extract the corresponding word alignments
        # Ensure we don't go out of bounds
        ayah_start_idx = max(0, ayah_start_idx)
        ayah_end_idx = min(len(word_alignments), ayah_end_idx)
        
        if ayah_start_idx >= len(word_alignments):
            self.logger.warning(f"Ayah start index {ayah_start_idx} exceeds word alignments length {len(word_alignments)}")
            return None
        
        ayah_word_alignments = word_alignments[ayah_start_idx:ayah_end_idx]
        
        if not ayah_word_alignments:
            return None
        
        # Get timing from first and last word
        start_time = ayah_word_alignments[0]['start']
        end_time = ayah_word_alignments[-1]['end']
        
        return {
            'start_time': start_time,
            'end_time': end_time,
            'word_alignments': ayah_word_alignments
        }
    
    def _fuzzy_find_ayah_words(self, ayah_words, chunk_words, threshold=0.7):
        """
        Fuzzy match ayah words in chunk words.
        
        Allows for some words to be different (e.g., due to normalization differences).
        
        Args:
            ayah_words: List of words in the ayah
            chunk_words: List of words in the chunk
            threshold: Minimum ratio of matching words
            
        Returns:
            Tuple of (start_idx, end_idx) or (None, None)
        """
        best_match_ratio = 0
        best_start_idx = None
        best_end_idx = None
        
        for i in range(len(chunk_words) - len(ayah_words) + 1):
            matches = 0
            for j, ayah_word in enumerate(ayah_words):
                if i + j < len(chunk_words) and chunk_words[i + j] == ayah_word:
                    matches += 1
            
            match_ratio = matches / len(ayah_words) if ayah_words else 0
            
            if match_ratio > best_match_ratio:
                best_match_ratio = match_ratio
                best_start_idx = i
                best_end_idx = i + len(ayah_words)
        
        if best_match_ratio >= threshold:
            return best_start_idx, best_end_idx
        
        return None, None
