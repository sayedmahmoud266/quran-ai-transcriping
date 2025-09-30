"""
Quran data utilities for verse matching and retrieval.
This module provides functionality to match transcribed text to Quran verses.
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher


class QuranData:
    """
    Handles Quran verse data and matching operations.
    In a production environment, this would load from a proper Quran database.
    For now, we'll use a simplified approach with basic verse matching.
    """
    
    def __init__(self):
        # This is a simplified version. In production, load from a complete Quran database
        # For demonstration, we'll use a pattern-based approach
        self.verses_cache = {}
    
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
        In production, this would query a Quran database.
        For now, returns a placeholder that should be replaced with actual data.
        """
        # This is a placeholder - in production, load from Quran database
        # You would typically use a library like quran-json or tanzil database
        return f"[Verse {surah}:{ayah} with tashkeel]"
    
    def count_words(self, text: str) -> int:
        """Count words in Arabic text."""
        return len(text.strip().split())
    
    def match_verses(self, transcription: str) -> List[Dict]:
        """
        Match transcribed text to Quran verses.
        This is a simplified implementation. In production, use a proper Quran database
        with fuzzy matching capabilities.
        
        Args:
            transcription: The transcribed Arabic text
            
        Returns:
            List of matched verses with details
        """
        # Normalize the transcription
        normalized = self.normalize_arabic_text(transcription)
        
        # In production, implement proper verse matching using a Quran database
        # For now, return a structure that demonstrates the expected format
        # This should be replaced with actual Quran verse matching logic
        
        verses = []
        
        # Example structure - replace with actual matching logic
        # This is just to demonstrate the expected output format
        words = normalized.split()
        
        # Placeholder: In production, implement actual verse detection
        # using a Quran database and fuzzy matching
        
        return verses
    
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
