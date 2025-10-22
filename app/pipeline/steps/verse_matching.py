"""
Verse Matching Step - Step 7 of the pipeline.

Matches transcribed text to Quran verses.
"""

from app.pipeline.base import PipelineStep, PipelineContext
import quran_ayah_lookup as qal
from rapidfuzz import fuzz, process

class VerseMatchingStep(PipelineStep):
    """
    Match transcription to Quran verses.
    
    Input (from context):
        - final_transcription: Combined transcription
        - chunks: Chunk boundaries (for hints)
    
    Output (to context):
        - matched_verses: List of matched verses
    
    Note: Implement your own verse matching logic here.
    """
    
    def __init__(self):
        """
        Initialize verse matching step.
        """
        super().__init__()
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that transcription is present."""
        if not context.final_transcription:
            self.logger.error("No final transcription in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Match verses.
        
        TODO: Implement verse matching logic
        """
        ctn = context.combined_transcription_normalized

        """
            
        results is list of data class with the following attributes    
        Attributes:
            verses (List[QuranVerse]): List of verses in the match (ordered)
            similarity (float): Similarity score (0.0-100.0)
            matched_text (str): The actual text segment that was matched
            query_text (str): The original query text used for matching
            start_surah (int): Starting surah number
            start_ayah (int): Starting ayah number
            start_word (int): Starting word index within the first ayah (0-based)
            end_surah (int): Ending surah number
            end_ayah (int): Ending ayah number
            end_word (int): Ending word index within the last ayah (exclusive)
        

        each verse of results[*].verse is a data class of the followi
        Attributes:
            surah_number (int): The surah number (1-114)
            ayah_number (int): The ayah number within the surah (0 for Basmala, 1+ for regular ayahs)
            text (str): The original Arabic text with all diacritics
            text_normalized (str): The normalized Arabic text without diacritics
            is_basmalah (bool): True if this is a Basmala verse (ayah_number = 0)
        """
        self.logger.info(f"Matching verses for transcription ({len(ctn)} chars)...")
        
        results = qal.search_sliding_window(ctn)
        
        # Check if we have results
        if not results:
            self.logger.warning("No verse matches found")
            context.matched_verses = []
            context.match_similarity = 0.0
            context.match_boundaries = {}
            return context
        
        # Pick the result with highest similarity
        best_match = max(results, key=lambda r: r.similarity)
        
        self.logger.info(f"Best match found with {best_match.similarity:.2f}% similarity")
        
        # Extract matched ayahs with all details
        matched_ayahs = []
        for verse in best_match.verses:
            ayah_data = {
                'surah_number': verse.surah_number,
                'ayah_number': verse.ayah_number,
                'text': verse.text,
                'text_normalized': verse.text_normalized,
                'is_basmalah': verse.is_basmalah
            }
            matched_ayahs.append(ayah_data)
        
        # Extract match boundaries
        match_boundaries = {
            'start_surah': best_match.start_surah,
            'start_ayah': best_match.start_ayah,
            'start_word': best_match.start_word,
            'end_surah': best_match.end_surah,
            'end_ayah': best_match.end_ayah,
            'end_word': best_match.end_word
        }
        
        # Store in context
        context.matched_verses = best_match.verses  # Keep original verse objects
        context.matched_ayahs = matched_ayahs  # Extracted data
        context.match_similarity = best_match.similarity
        context.match_boundaries = match_boundaries
        context.matched_text = best_match.matched_text
        context.query_text = best_match.query_text
        
        self.logger.info(
            f"Matched {len(matched_ayahs)} ayahs from Surah {match_boundaries['start_surah']}:"
            f"{match_boundaries['start_ayah']} to Surah {match_boundaries['end_surah']}:"
            f"{match_boundaries['end_ayah']}"
        )
        
        # Map each transcription chunk to matched ayahs
        self.logger.info("Mapping chunks to matched ayahs...")
        
        transcriptions = context.transcriptions
        matched_chunk_verses = []
        
        # Create a mapping of verses for fuzzy matching
        # Build a list of verse texts with their metadata
        # Only include verses within the found boundaries
        verse_mapping = []
        for verse in best_match.verses:
            # Check if verse is within boundaries
            verse_position = (verse.surah_number, verse.ayah_number)
            start_position = (match_boundaries['start_surah'], match_boundaries['start_ayah'])
            end_position = (match_boundaries['end_surah'], match_boundaries['end_ayah'])
            
            # Include verse only if it's within the boundary range
            if start_position <= verse_position <= end_position:
                verse_mapping.append({
                    'text_normalized': verse.text_normalized,
                    'surah_number': verse.surah_number,
                    'ayah_number': verse.ayah_number,
                    'text': verse.text,
                    'is_basmalah': verse.is_basmalah
                })
        
        for transcription in transcriptions:
            chunk_normalized = transcription.get('normalized_text', '')
            
            if not chunk_normalized:
                continue
            
            # Use rapidfuzz to find the best matching verse(s) for this chunk
            # We'll use partial_ratio for fuzzy partial matching
            best_matches = []
            for verse_data in verse_mapping:
                score = fuzz.partial_ratio(chunk_normalized, verse_data['text_normalized'])
                if score >= 85:  # Threshold for considering a match (85%)
                    best_matches.append({
                        'verse_data': verse_data,
                        'score': score
                    })
            
            # Sort by score and take the best matches
            best_matches.sort(key=lambda x: x['score'], reverse=True)
            
            if best_matches:
                # Extract ayahs for this chunk (take top matches)
                chunk_ayahs = []
                seen_verses = set()
                
                for match in best_matches[:5]:  # Take top 5 matches
                    verse_data = match['verse_data']
                    verse_key = (verse_data['surah_number'], verse_data['ayah_number'])
                    
                    if verse_key not in seen_verses:
                        chunk_ayahs.append({
                            'surah_number': verse_data['surah_number'],
                            'ayah_number': verse_data['ayah_number'],
                            'text': verse_data['text'],
                            'text_normalized': verse_data['text_normalized'],
                            'is_basmalah': verse_data['is_basmalah'],
                            'similarity': match['score']
                        })
                        seen_verses.add(verse_key)
                
                # Determine boundaries based on matched ayahs
                if chunk_ayahs:
                    chunk_boundaries = {
                        'start_surah': chunk_ayahs[0]['surah_number'],
                        'start_ayah': chunk_ayahs[0]['ayah_number'],
                        'start_word': 0,
                        'end_surah': chunk_ayahs[-1]['surah_number'],
                        'end_ayah': chunk_ayahs[-1]['ayah_number'],
                        'end_word': len(chunk_ayahs[-1]['text_normalized'].split())
                    }
                    
                    matched_chunk_verses.append({
                        'chunk_index': transcription.get('chunk_index'),
                        'chunk_start_time': transcription.get('start_time'),
                        'chunk_end_time': transcription.get('end_time'),
                        'chunk_text': transcription.get('text'),
                        'chunk_normalized_text': chunk_normalized,
                        'matched_ayahs': chunk_ayahs,
                        'boundaries': chunk_boundaries,
                        'similarity': best_matches[0]['score'],
                        'matched_text': chunk_ayahs[0]['text_normalized']
                    })
                    
                    self.logger.debug(
                        f"Chunk {transcription.get('chunk_index')}: Matched {len(chunk_ayahs)} ayahs "
                        f"with {best_matches[0]['score']:.2f}% similarity"
                    )
            else:
                self.logger.warning(
                    f"Chunk {transcription.get('chunk_index')}: No matches found"
                )
        
        context.matched_chunk_verses = matched_chunk_verses
        
        self.logger.info(f"Mapped {len(matched_chunk_verses)} chunks to verses")
        
        context.add_debug_info(self.name, {
            'total_verses': len(matched_ayahs),
            'similarity': best_match.similarity,
            'matched_ayahs': matched_ayahs,
            'match_boundaries': match_boundaries,
            'matched_text': best_match.matched_text,
            'query_text': best_match.query_text,
            'total_results': len(results),
            'matched_chunk_verses': matched_chunk_verses,
            'total_mapped_chunks': len(matched_chunk_verses)
        })
        
        return context
