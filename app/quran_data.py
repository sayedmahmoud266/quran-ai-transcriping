"""
Quran data utilities for verse matching and retrieval.
This module provides functionality to match transcribed text to Quran verses.
"""

import json
import re
import os
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import requests
import pyarabic.araby as araby
from rapidfuzz import fuzz
import logging

logger = logging.getLogger(__name__)


class QuranData:
    """
    Handles Quran verse data and matching operations.
    Loads Quran text from Tanzil API and provides verse matching functionality.
    """
    
    def __init__(self):
        self.verses_cache = {}
        self.quran_data = []  # List of all verses with metadata
        self.normalized_verses = {}  # Normalized text for matching
        self.quran_text_with_tashkeel = {}  # Verse text with diacritics
        self._load_quran_data()
    
    def _load_quran_data(self):
        """
        Load Quran data from Tanzil simple text format.
        Downloads if not cached locally.
        """
        cache_file = "quran_simple.txt"
        
        try:
            # Try to load from cache
            if os.path.exists(cache_file):
                logger.info("Loading Quran data from cache...")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                # Download from Tanzil
                logger.info("Downloading Quran data from Tanzil...")
                url = "https://tanzil.net/trans/?transID=en.sahih&type=txt-2"
                # Using simple text version without tashkeel for matching
                simple_url = "https://raw.githubusercontent.com/risan/quran-json/master/dist/quran.json"
                
                try:
                    response = requests.get(simple_url, timeout=30)
                    response.raise_for_status()
                    quran_json = response.json()
                    
                    # Save to cache and process
                    lines = []
                    for verse in quran_json:
                        surah = verse['surah']
                        ayah = verse['ayah']
                        text = verse['text']
                        lines.append(f"{surah}|{ayah}|{text}\n")
                    
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                except Exception as e:
                    logger.error(f"Failed to download Quran data: {e}")
                    # Use minimal fallback data
                    self._use_fallback_data()
                    return
            
            # Parse the data
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('|')
                if len(parts) >= 3:
                    surah = int(parts[0])
                    ayah = int(parts[1])
                    text = parts[2]
                    
                    # Store verse data
                    verse_key = f"{surah}:{ayah}"
                    self.quran_text_with_tashkeel[verse_key] = text
                    
                    # Store normalized version for matching
                    normalized = self.normalize_arabic_text(text)
                    self.normalized_verses[verse_key] = normalized
                    
                    # Store in list for sequential access
                    self.quran_data.append({
                        'surah': surah,
                        'ayah': ayah,
                        'text': text,
                        'normalized': normalized,
                        'word_count': len(normalized.split())
                    })
            
            logger.info(f"Loaded {len(self.quran_data)} verses from Quran")
            
        except Exception as e:
            logger.error(f"Error loading Quran data: {e}")
            self._use_fallback_data()
    
    def _use_fallback_data(self):
        """
        Use minimal fallback data if download fails.
        """
        logger.warning("Using fallback Quran data (limited)")
        # Add some common verses as fallback
        fallback_verses = [
            (1, 1, "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"),
            (1, 2, "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ"),
            (1, 3, "الرَّحْمَٰنِ الرَّحِيمِ"),
            (1, 4, "مَالِكِ يَوْمِ الدِّينِ"),
            (1, 5, "إِيَّاكَ نَعْبُدُ وَإِيَّاكَ نَسْتَعِينُ"),
            (1, 6, "اهْدِنَا الصِّرَاطَ الْمُسْتَقِيمَ"),
            (1, 7, "صِرَاطَ الَّذِينَ أَنْعَمْتَ عَلَيْهِمْ غَيْرِ الْمَغْضُوبِ عَلَيْهِمْ وَلَا الضَّالِّينَ"),
        ]
        
        for surah, ayah, text in fallback_verses:
            verse_key = f"{surah}:{ayah}"
            self.quran_text_with_tashkeel[verse_key] = text
            normalized = self.normalize_arabic_text(text)
            self.normalized_verses[verse_key] = normalized
            self.quran_data.append({
                'surah': surah,
                'ayah': ayah,
                'text': text,
                'normalized': normalized,
                'word_count': len(normalized.split())
            })
    
    def normalize_arabic_text(self, text: str) -> str:
        """
        Normalize Arabic text by removing diacritics and extra spaces.
        """
        # Remove Arabic diacritics (tashkeel)
        arabic_diacritics = re.compile("""
            ّ    | # Shadda
            َ    | # Fatha
            ً    | # Tanween Fath
            ُ    | # Damma
            ٌ    | # Tanween Damm
            ِ    | # Kasra
            ٍ    | # Tanween Kasr
            ْ    | # Sukun
            ـ     # Tatweel/Kashida
        """, re.VERBOSE)
        
        text = re.sub(arabic_diacritics, '', text)
        text = ' '.join(text.split())  # Normalize whitespace
        return text.strip()
    
    def get_verse_with_tashkeel(self, surah: int, ayah: int) -> str:
        """
        Get verse text with tashkeel (diacritics).
        """
        verse_key = f"{surah}:{ayah}"
        return self.quran_text_with_tashkeel.get(verse_key, f"[Verse {surah}:{ayah}]")
    
    def count_words(self, text: str) -> int:
        """Count words in Arabic text."""
        return len(text.strip().split())
    
    def match_verses(self, transcription: str, chunk_boundaries: List[Dict] = None) -> List[Dict]:
        """
        Match transcribed text to Quran verses using fuzzy matching.
        Uses chunk boundaries as hints for verse detection.
        
        Args:
            transcription: The transcribed Arabic text
            chunk_boundaries: Optional list of audio chunk info for verse boundary hints
            
        Returns:
            List of matched verses with details
        """
        if not self.quran_data:
            logger.warning("No Quran data loaded")
            return []
        
        # Normalize the transcription
        normalized = self.normalize_arabic_text(transcription)
        
        if not normalized:
            return []
        
        # Find best matching verses
        matched_verses = self._find_matching_verses(normalized, chunk_boundaries)
        
        return matched_verses
    
    def _find_matching_verses(self, normalized_text: str, chunk_boundaries: List[Dict] = None) -> List[Dict]:
        """
        Find verses that match the normalized text using fuzzy matching.
        """
        words = normalized_text.split()
        if not words:
            return []
        
        # If we have chunk boundaries, use them as hints
        if chunk_boundaries and len(chunk_boundaries) > 1:
            return self._match_with_chunk_hints(normalized_text, chunk_boundaries)
        
        # Otherwise, do a sliding window search
        return self._match_sliding_window(normalized_text)
    
    def _match_with_chunk_hints(self, normalized_text: str, chunk_boundaries: List[Dict]) -> List[Dict]:
        """
        Match verses using chunk boundaries as hints for verse breaks.
        """
        matched_verses = []
        
        # Split transcription by chunks
        words = normalized_text.split()
        chunk_texts = []
        
        # Approximate word distribution across chunks
        total_words = len(words)
        words_per_chunk = total_words // len(chunk_boundaries) if chunk_boundaries else total_words
        
        start_idx = 0
        for i, chunk in enumerate(chunk_boundaries):
            end_idx = min(start_idx + words_per_chunk, total_words)
            if i == len(chunk_boundaries) - 1:
                end_idx = total_words
            
            chunk_text = ' '.join(words[start_idx:end_idx])
            if chunk_text:
                chunk_texts.append({
                    'text': chunk_text,
                    'start_time': chunk.get('start_time', 0),
                    'end_time': chunk.get('end_time', 0)
                })
            start_idx = end_idx
        
        # Match each chunk to verses
        for chunk_info in chunk_texts:
            best_match = self._find_best_verse_match(chunk_info['text'])
            if best_match:
                best_match['audio_start_time'] = chunk_info['start_time']
                best_match['audio_end_time'] = chunk_info['end_time']
                matched_verses.append(best_match)
        
        return matched_verses
    
    def _match_sliding_window(self, normalized_text: str) -> List[Dict]:
        """
        Match verses using a sliding window approach for consecutive ayahs.
        """
        # Try to find consecutive verses in the text
        consecutive_matches = self._find_consecutive_verses(normalized_text)
        if consecutive_matches:
            return consecutive_matches
        
        # Fallback to single best match
        best_match = self._find_best_verse_match(normalized_text)
        if best_match:
            return [best_match]
        return []
    
    def _is_basmala(self, text: str) -> bool:
        """
        Check if the text is Basmala (بسم الله الرحمن الرحيم).
        """
        basmala_normalized = self.normalize_arabic_text("بسم الله الرحمن الرحيم")
        text_normalized = self.normalize_arabic_text(text)
        
        # Check if text contains or is very similar to Basmala
        if basmala_normalized in text_normalized or text_normalized in basmala_normalized:
            return True
        
        # Check similarity
        similarity = fuzz.ratio(text_normalized, basmala_normalized) / 100.0
        return similarity >= 0.85
    
    def _find_consecutive_verses(self, text: str, min_similarity: float = 0.6) -> List[Dict]:
        """
        Find consecutive verses in the transcribed text.
        Handles Basmala detection and multi-ayah sequences.
        """
        words = text.split()
        if len(words) < 3:
            return []
        
        matched_verses = []
        
        # Check if text starts with Basmala
        basmala_text = ' '.join(words[:4]) if len(words) >= 4 else text
        has_basmala = self._is_basmala(basmala_text)
        
        if has_basmala:
            # Try to identify the surah from the following text
            remaining_text = ' '.join(words[4:]) if len(words) > 4 else ""
            
            if remaining_text:
                # Find the first verse after Basmala
                next_verse = self._find_best_verse_match(remaining_text, min_similarity=0.65)
                
                if next_verse:
                    surah_num = next_verse['surah']
                    
                    # Add Basmala entry
                    # Surah 1 (Al-Fatiha): Basmala is ayah 1
                    # Surah 9 (At-Tawbah): No Basmala
                    # Other surahs: Basmala is ayah 0 (not numbered)
                    if surah_num == 1:
                        basmala_entry = {
                            'surah': 1,
                            'ayah': 1,
                            'text': self.get_verse_with_tashkeel(1, 1),
                            'similarity': 0.95,
                            'is_basmala': True
                        }
                    else:
                        basmala_entry = {
                            'surah': surah_num,
                            'ayah': 0,
                            'text': "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                            'similarity': 0.95,
                            'is_basmala': True
                        }
                    matched_verses.append(basmala_entry)
                    
                    # Add the following verse(s)
                    following_verses = self._find_verse_sequence(remaining_text, surah_num, next_verse['ayah'])
                    matched_verses.extend(following_verses)
                    
                    return matched_verses
        
        # No Basmala detected, try to find consecutive verses
        return self._find_verse_sequence(text)
    
    def _find_verse_sequence(self, text: str, expected_surah: int = None, start_ayah: int = None) -> List[Dict]:
        """
        Find a sequence of consecutive verses in the text.
        
        Args:
            text: Normalized text to search
            expected_surah: Expected surah number (if known from context)
            start_ayah: Expected starting ayah (if known from context)
        """
        if not text.strip():
            return []
        
        words = text.split()
        if len(words) < 3:
            # Too short, try single match
            match = self._find_best_verse_match(text)
            return [match] if match else []
        
        matched_verses = []
        
        # Try to find the first verse
        first_match = self._find_best_verse_match(text, min_similarity=0.6)
        
        if not first_match:
            return []
        
        current_surah = expected_surah if expected_surah else first_match['surah']
        current_ayah = start_ayah if start_ayah else first_match['ayah']
        
        # Try to match consecutive verses
        remaining_text = text
        max_verses = 10  # Limit to prevent infinite loops
        
        for _ in range(max_verses):
            # Get the expected verse
            verse_key = f"{current_surah}:{current_ayah}"
            expected_verse_text = self.normalized_verses.get(verse_key, "")
            
            if not expected_verse_text:
                break
            
            # Check if remaining text starts with this verse
            similarity = fuzz.partial_ratio(remaining_text, expected_verse_text) / 100.0
            
            if similarity >= 0.6:
                # Found a match
                verse_data = self._get_verse_by_key(current_surah, current_ayah)
                if verse_data:
                    matched_verses.append({
                        'surah': current_surah,
                        'ayah': current_ayah,
                        'text': verse_data['text'],
                        'similarity': similarity
                    })
                    
                    # Remove matched portion from remaining text
                    verse_words = expected_verse_text.split()
                    remaining_words = remaining_text.split()
                    
                    # Estimate how many words were matched
                    words_to_remove = min(len(verse_words), len(remaining_words))
                    remaining_text = ' '.join(remaining_words[words_to_remove:])
                    
                    if not remaining_text.strip():
                        break
                    
                    # Move to next ayah
                    current_ayah += 1
                else:
                    break
            else:
                break
        
        return matched_verses if matched_verses else ([first_match] if first_match else [])
    
    def _get_verse_by_key(self, surah: int, ayah: int) -> Optional[Dict]:
        """
        Get verse data by surah and ayah number.
        """
        for verse in self.quran_data:
            if verse['surah'] == surah and verse['ayah'] == ayah:
                return verse
        return None
    
    def _find_best_verse_match(self, text: str, min_similarity: float = 0.6) -> Optional[Dict]:
        """
        Find the best matching verse for given text using fuzzy string matching.
        Uses rapidfuzz for fast similarity calculation.
        """
        best_score = 0
        best_verse = None
        
        # Search through all verses
        for verse in self.quran_data:
            # Calculate similarity using rapidfuzz (returns 0-100, normalize to 0-1)
            similarity = fuzz.ratio(text, verse['normalized']) / 100.0
            
            # Also check if text is a substring (for partial matches)
            if text in verse['normalized'] or verse['normalized'] in text:
                similarity = max(similarity, 0.8)
            
            if similarity > best_score and similarity >= min_similarity:
                best_score = similarity
                best_verse = verse
        
        if best_verse:
            return {
                'surah': best_verse['surah'],
                'ayah': best_verse['ayah'],
                'text': best_verse['text'],
                'similarity': best_score
            }
        
        return None
    
    def get_verse_details(self, surah: int, ayah: int, 
                         start_word: int, end_word: int,
                         start_time: float, end_time: float) -> Dict:
        """
        Get detailed information about a verse.
        
        Args:
            surah: Surah number
            ayah: Ayah number
            start_word: Starting word index in the ayah
            end_word: Ending word index in the ayah
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            
        Returns:
            Dictionary with verse details
        """
        verse_text = self.get_verse_with_tashkeel(surah, ayah)
        word_count = self.count_words(verse_text)
        
        return {
            "surah_number": surah,
            "ayah_number": ayah,
            "ayah_text_tashkeel": verse_text,
            "ayah_word_count": word_count,
            "start_from_word": start_word,
            "end_to_word": end_word,
            "audio_start_timestamp": self._format_timestamp(start_time),
            "audio_end_timestamp": self._format_timestamp(end_time)
        }
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp from seconds to HH:MM:SS.mmm format.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


# Singleton instance
quran_data = QuranData()
