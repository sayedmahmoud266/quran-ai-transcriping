"""
Quran data utilities for verse matching and retrieval.

This module provides basic Quran data loading and text normalization.
Verse matching algorithms have been removed and need to be reimplemented.
"""

import json
import re
import os
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

try:
    import pyquran
    PYQURAN_AVAILABLE = True
    print("✓ pyquran library loaded successfully")
except ImportError as e:
    PYQURAN_AVAILABLE = False
    pyquran = None
    print(f"✗ pyquran not available: {e}")


class QuranData:
    """
    Handles Quran verse data and basic text operations.
    Loads Quran text from PyQuran and Uthmani text file for complete tashkeel.
    """
    
    def __init__(self):
        self.verses_cache = {}
        self.quran_data = []  # List of all verses with metadata
        self.normalized_verses = {}  # Normalized text for matching
        self.quran_text_with_tashkeel = {}  # Verse text with diacritics from PyQuran
        self.quran_uthmani_text = {}  # Verse text with full Uthmani tashkeel and tilawah marks
        self._load_quran_data()
        self._load_uthmani_text()
    
    def _load_quran_data(self):
        """
        Load Quran data using pyquran library or fallback methods.
        """
        try:
            print(f"→ PYQURAN_AVAILABLE = {PYQURAN_AVAILABLE}")
            if PYQURAN_AVAILABLE:
                print("→ Loading Quran data using pyquran library...")
                self._load_from_pyquran()
                print(f"✓ Successfully loaded {len(self.quran_data)} verses from pyquran")
                logger.info(f"Successfully loaded {len(self.quran_data)} verses from pyquran")
            else:
                print("→ pyquran not available, using fallback data")
                logger.warning("pyquran not available, using fallback data")
                self._use_fallback_data()
                
        except Exception as e:
            print(f"✗ Error loading Quran data: {e}")
            logger.error(f"Error loading Quran data: {e}")
            import traceback
            traceback.print_exc()
            self._use_fallback_data()
    
    def _load_from_pyquran(self):
        """
        Load Quran data using the pyquran library.
        """
        try:
            # Load all 114 surahs
            for surah_num in range(1, 115):
                try:
                    # Get surah verses as a list (with tashkeel)
                    surah_verses = pyquran.quran.get_sura(surah_num, with_tashkeel=True, basmalah=False)
                    
                    # Process each ayah in the surah
                    for ayah_index, verse_text in enumerate(surah_verses):
                        ayah_num = ayah_index + 1  # Ayah numbers start at 1
                        
                        if verse_text:
                            # Store verse data
                            verse_key = f"{surah_num}:{ayah_num}"
                            self.quran_text_with_tashkeel[verse_key] = verse_text
                            
                            # Store normalized version for matching
                            normalized = self.normalize_arabic_text(verse_text)
                            self.normalized_verses[verse_key] = normalized
                            
                            # Store in list for sequential access
                            self.quran_data.append({
                                'surah': surah_num,
                                'ayah': ayah_num,
                                'text': verse_text,
                                'normalized': normalized,
                                'word_count': len(normalized.split())
                            })
                            
                except Exception as e:
                    logger.debug(f"Error loading surah {surah_num}: {e}")
                    continue
            
            logger.info(f"Loaded {len(self.quran_data)} verses from pyquran")
            
            if len(self.quran_data) == 0:
                raise ValueError("No verses loaded from pyquran")
                
        except Exception as e:
            logger.error(f"Failed to load from pyquran: {e}")
            raise
    
    def _use_fallback_data(self):
        """
        Use minimal fallback data if download fails.
        Includes common short surahs for testing.
        """
        logger.warning("Using fallback Quran data (limited to common surahs)")
        # Add common verses as fallback - Surah 1, 111, 112, 113, 114
        fallback_verses = [
            # Surah 1 - Al-Fatiha
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
    
    def _load_uthmani_text(self):
        """
        Load Quran text with full Uthmani tashkeel and tilawah marks from res/quran-uthmani_all.txt.
        Format: surah|ayah|text
        """
        try:
            # Get the path to the Uthmani text file
            base_dir = Path(__file__).parent.parent
            uthmani_file = base_dir / "res" / "quran-uthmani_all.txt"
            
            if not uthmani_file.exists():
                logger.warning(f"Uthmani text file not found: {uthmani_file}")
                return
            
            logger.info(f"Loading Uthmani text from: {uthmani_file}")
            
            with open(uthmani_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('|')
                    if len(parts) != 3:
                        logger.warning(f"Invalid line format at line {line_num}: {line[:50]}")
                        continue
                    
                    try:
                        surah = int(parts[0])
                        ayah = int(parts[1])
                        text = parts[2]
                        
                        verse_key = f"{surah}:{ayah}"
                        self.quran_uthmani_text[verse_key] = text
                        
                    except ValueError as e:
                        logger.warning(f"Error parsing line {line_num}: {e}")
                        continue
            
            logger.info(f"Loaded {len(self.quran_uthmani_text)} verses with Uthmani text")
            
        except Exception as e:
            logger.error(f"Error loading Uthmani text: {e}", exc_info=True)
    
    def normalize_arabic_text(self, text: str) -> str:
        """
        Normalize Arabic text by removing all diacritics, tilawah marks, and extra spaces.
        Comprehensive removal of tashkeel, harakat, tanween, and Quranic marks.
        """
        if not text:
            return ""
        
        # Remove all Arabic diacritics and marks
        # This includes: tashkeel, harakat, tanween, sukun, shadda, maddah, hamza marks, etc.
        text = re.sub(r'[\u064B-\u065F\u0670\u0610-\u061A\u06D6-\u06ED]', '', text)
        
        # Normalize Arabic letters
        text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        text = text.replace('ة', 'ه')  # Normalize taa marbuta
        
        # Remove extra whitespace
        text = ' '.join(text.split())  # Normalize whitespace
        return text.strip()
    
    def get_verse_with_tashkeel(self, surah: int, ayah: int) -> str:
        """
        Get verse text with full Uthmani tashkeel and tilawah marks.
        Falls back to PyQuran text if Uthmani text is not available.
        """
        verse_key = f"{surah}:{ayah}"
        
        # Try Uthmani text first (most complete)
        if verse_key in self.quran_uthmani_text:
            return self.quran_uthmani_text[verse_key]
        
        # Fallback to PyQuran text
        if verse_key in self.quran_text_with_tashkeel:
            return self.quran_text_with_tashkeel[verse_key]
        
        # Last resort
        return f"[Verse {surah}:{ayah}]"
    
    def count_words(self, text: str) -> int:
        """Count words in Arabic text."""
        return len(text.strip().split())
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp from seconds to HH:MM:SS.mmm format.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    # TODO: Add new verse matching methods here
    # Examples:
    # - match_verses() - Main verse matching function
    # - _find_matching_verses() - Find verses using fuzzy matching
    # - _find_consecutive_verses() - Find consecutive verse sequences
    # - _is_basmala() - Check if text is Basmala


# Singleton instance
quran_data = QuranData()
