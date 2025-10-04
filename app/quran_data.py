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
    Handles Quran verse data and matching operations.
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
            # Surah 111 - Al-Masad
            (111, 1, "تَبَّتْ يَدَا أَبِي لَهَبٍ وَتَبَّ"),
            (111, 2, "مَا أَغْنَىٰ عَنْهُ مَالُهُ وَمَا كَسَبَ"),
            (111, 3, "سَيَصْلَىٰ نَارًا ذَاتَ لَهَبٍ"),
            (111, 4, "وَامْرَأَتُهُ حَمَّالَةَ الْحَطَبِ"),
            (111, 5, "فِي جِيدِهَا حَبْلٌ مِّن مَّسَدٍ"),
            # Surah 112 - Al-Ikhlas
            (112, 1, "قُلْ هُوَ اللَّهُ أَحَدٌ"),
            (112, 2, "اللَّهُ الصَّمَدُ"),
            (112, 3, "لَمْ يَلِدْ وَلَمْ يُولَدْ"),
            (112, 4, "وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ"),
            # Surah 113 - Al-Falaq
            (113, 1, "قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ"),
            (113, 2, "مِن شَرِّ مَا خَلَقَ"),
            (113, 3, "وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ"),
            (113, 4, "وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ"),
            (113, 5, "وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ"),
            # Surah 114 - An-Nas
            (114, 1, "قُلْ أَعُوذُ بِرَبِّ النَّاسِ"),
            (114, 2, "مَلِكِ النَّاسِ"),
            (114, 3, "إِلَٰهِ النَّاسِ"),
            (114, 4, "مِن شَرِّ الْوَسْوَاسِ الْخَنَّاسِ"),
            (114, 5, "الَّذِي يُوَسْوِسُ فِي صُدُورِ النَّاسِ"),
            (114, 6, "مِنَ الْجِنَّةِ وَالنَّاسِ"),
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
        Note: Surahs (except Fatiha and Tawbah) have Basmala prefixed to ayah 1, which we extract as ayah 0.
        """
        try:
            uthmani_file = Path(__file__).parent.parent / "res" / "quran-uthmani_all.txt"
            
            if not uthmani_file.exists():
                logger.warning(f"Uthmani text file not found at {uthmani_file}")
                return
            
            logger.info(f"Loading Uthmani text from {uthmani_file}")
            
            basmala_text = "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ"
            
            with open(uthmani_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    parts = line.split('|')
                    if len(parts) != 3:
                        continue
                    
                    try:
                        surah_num = int(parts[0])
                        ayah_num = int(parts[1])
                        ayah_text = parts[2]
                        
                        # For surahs except Fatiha (1) and Tawbah (9), ayah 1 has Basmala prefixed
                        if surah_num not in [1, 9] and ayah_num == 1:
                            # Check if text starts with Basmala
                            if ayah_text.startswith(basmala_text):
                                # Extract Basmala as ayah 0
                                self.quran_uthmani_text[f"{surah_num}:0"] = basmala_text
                                
                                # Remove Basmala from ayah 1 text
                                ayah_text_without_basmala = ayah_text[len(basmala_text):].strip()
                                self.quran_uthmani_text[f"{surah_num}:{ayah_num}"] = ayah_text_without_basmala
                            else:
                                # No Basmala found, store as is
                                self.quran_uthmani_text[f"{surah_num}:{ayah_num}"] = ayah_text
                        else:
                            # Store as is for Fatiha, Tawbah, and other ayahs
                            self.quran_uthmani_text[f"{surah_num}:{ayah_num}"] = ayah_text
                    
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Error parsing line: {line} - {e}")
                        continue
            
            logger.info(f"Loaded {len(self.quran_uthmani_text)} Uthmani verses")
            
        except Exception as e:
            logger.error(f"Error loading Uthmani text: {e}", exc_info=True)
    
    def normalize_arabic_text(self, text: str) -> str:
        """
        Normalize Arabic text by removing all diacritics, tilawah marks, and extra spaces.
        Comprehensive removal of tashkeel, harakat, tanween, and Quranic marks.
        """
        # Remove all Arabic diacritics and Quranic marks
        arabic_diacritics = re.compile("""
            [\u064B-\u065F]  | # Arabic harakat and tanween (ً ٌ ٍ َ ُ ِ ّ ْ ٓ ٔ ٕ ٖ ٗ ٘ ٙ ٚ ٛ ٜ ٝ ٞ ٟ)
            [\u0670]        | # Superscript alef (ٰ) - the madd symbol
            [\u0610-\u061A] | # Additional Arabic marks
            [\u06D6-\u06DC] | # Small high marks (ۖ ۗ ۘ ۙ ۚ ۛ ۜ)
            [\u06DF-\u06E8] | # Additional Quranic marks (ۡ ۢ ۣ ۤ ۥ ۦ ۧ ۨ)
            [\u06EA-\u06ED] | # More Quranic marks (۪ ۫ ۬ ۭ)
            [\u08D4-\u08E1] | # Extended Arabic marks
            [\u08E3-\u08FF] | # More extended marks
            [\u0640]        | # Tatweel/Kashida (ـ)
            [\u06DD]        | # End of ayah (۝)
            [\u06DE]        | # Start of rub el hizb (۞)
            [\u06E9]        | # Place of sajdah (۩)
        """, re.VERBOSE)
        
        text = re.sub(arabic_diacritics, '', text)
        text = ' '.join(text.split())  # Normalize whitespace
        return text.strip()
    
    def get_verse_with_tashkeel(self, surah: int, ayah: int) -> str:
        """
        Get verse text with full Uthmani tashkeel and tilawah marks.
        Falls back to PyQuran text if Uthmani text is not available.
        """
        verse_key = f"{surah}:{ayah}"
        
        # Try Uthmani text first (has full tashkeel and tilawah marks)
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
        Uses consecutive verse detection on the full text, then assigns timing from chunks.
        """
        # Use consecutive verse detection on the full text
        matched_verses = self._find_consecutive_verses(normalized_text)
        
        if not matched_verses:
            logger.warning("No verses matched with chunk hints")
            return []
        
        # Assign timing information from chunk boundaries
        if len(matched_verses) <= len(chunk_boundaries):
            # Assign each verse to a chunk
            for i, verse in enumerate(matched_verses):
                if i < len(chunk_boundaries):
                    verse['audio_start_time'] = chunk_boundaries[i].get('start_time', 0)
                    verse['audio_end_time'] = chunk_boundaries[i].get('end_time', 0)
        else:
            # More verses than chunks, distribute timing
            total_duration = chunk_boundaries[-1].get('end_time', 0) - chunk_boundaries[0].get('start_time', 0)
            verse_duration = total_duration / len(matched_verses) if matched_verses else 0
            start_time = chunk_boundaries[0].get('start_time', 0)
            
            for i, verse in enumerate(matched_verses):
                verse['audio_start_time'] = start_time + (i * verse_duration)
                verse['audio_end_time'] = start_time + ((i + 1) * verse_duration)
        
        logger.info(f"Matched {len(matched_verses)} verses with chunk hints")
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
    
    def _find_consecutive_verses(self, text: str, min_similarity: float = 0.6, min_coverage: float = 0.8) -> List[Dict]:
        """
        Find consecutive verses in the transcribed text with comprehensive matching.
        Ensures at least min_coverage (80%) of the text is accounted for.
        Handles Basmala, repetitions, and finds best consecutive ayah pattern.
        """
        words = text.split()
        if len(words) < 3:
            return []
        
        # Check if text starts with Basmala
        basmala_text = ' '.join(words[:4]) if len(words) >= 4 else text
        has_basmala = self._is_basmala(basmala_text)
        
        basmala_entry = None
        search_text = text
        
        if has_basmala:
            remaining_text = ' '.join(words[4:]) if len(words) > 4 else ""
            logger.info(f"Basmala detected, remaining text: {remaining_text[:100]}...")
            search_text = remaining_text
            
            # Don't create Basmala entry yet - let constraint propagation determine the surah
            # This will be added after we know the correct surah
        
        # Find all consecutive verses with comprehensive coverage
        matched_verses = self._find_comprehensive_verse_sequence(search_text, min_coverage)
        
        # Add Basmala at the beginning if detected and we found verses
        if has_basmala and matched_verses:
            surah_num = matched_verses[0]['surah']
            logger.info(f"Adding Basmala for Surah {surah_num}")
            
            if surah_num == 1:
                basmala_entry = {
                    'surah': 1, 'ayah': 1,
                    'text': self.get_verse_with_tashkeel(1, 1),
                    'similarity': 0.95, 'is_basmala': True
                }
            else:
                basmala_entry = {
                    'surah': surah_num, 'ayah': 0,
                    'text': "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
                    'similarity': 0.95, 'is_basmala': True
                }
            matched_verses.insert(0, basmala_entry)
        
        logger.info(f"Found {len(matched_verses)} verses (coverage check passed)")
        return matched_verses
    
    def _find_comprehensive_verse_sequence(self, text: str, min_coverage: float = 0.8) -> List[Dict]:
        """
        Comprehensive verse matching using constraint propagation.
        Progressively narrows down possibilities by intersecting matches from consecutive batches.
        """
        normalized_text = self.normalize_arabic_text(text)
        text_words = normalized_text.split()
        total_words = len(text_words)
        
        if total_words < 3:
            return []
        
        logger.info(f"Starting constraint propagation matching for {total_words} words")
        
        # Use constraint propagation to find the correct surah and starting ayah
        surah_num, start_ayah = self._find_surah_by_constraint_propagation(text_words)
        
        if not surah_num:
            logger.error("Could not determine surah using constraint propagation")
            return []
        
        logger.info(f"✓ Determined Surah {surah_num}, starting from Ayah {start_ayah}")
        
        # Check if we need to fill backward gaps (missing ayahs before start_ayah)
        # This happens when constraint propagation starts from ayah 4 but ayahs 1-3 are missing
        backward_verses = self._fill_backward_gaps(normalized_text, surah_num, start_ayah)
        
        original_start_ayah = start_ayah
        if backward_verses:
            logger.info(f"Filled {len(backward_verses)} backward gaps before ayah {start_ayah}")
            # Don't update start_ayah - we'll continue from original start_ayah in forward loop
        
        # Build sequence of consecutive verses from this surah
        matched_verses = backward_verses if backward_verses else []
        current_surah = surah_num
        current_ayah = original_start_ayah  # Start forward matching from original position
        matched_word_count = sum(len(v['text'].split()) for v in matched_verses)
        
        # Get all verses from this surah
        surah_verses = [v for v in self.quran_data if v['surah'] == current_surah]
        max_ayah = max(v['ayah'] for v in surah_verses) if surah_verses else 0
        
        # Match consecutive verses
        consecutive_misses = 0
        max_consecutive_misses = 5  # Allow up to 5 misses before stopping (for repeated phrases)
        
        for ayah_num in range(current_ayah, min(current_ayah + 100, max_ayah + 1)):
            verse_data = self._get_verse_by_key(current_surah, ayah_num)
            if not verse_data:
                break
            
            verse_normalized = verse_data['normalized']
            verse_words = verse_normalized.split()
            
            # Check if this verse appears in the text (exact or fuzzy)
            if verse_normalized in normalized_text:
                matched_verses.append({
                    'surah': current_surah,
                    'ayah': ayah_num,
                    'text': verse_data['text'],
                    'similarity': 1.0
                })
                matched_word_count += len(verse_words)
                consecutive_misses = 0
                logger.debug(f"  ✓ Matched {current_surah}:{ayah_num} (exact)")
            else:
                # Try fuzzy match
                similarity = fuzz.partial_ratio(verse_normalized, normalized_text) / 100.0
                if similarity >= 0.70:  # Lower threshold for better coverage
                    matched_verses.append({
                        'surah': current_surah,
                        'ayah': ayah_num,
                        'text': verse_data['text'],
                        'similarity': similarity
                    })
                    matched_word_count += len(verse_words)
                    consecutive_misses = 0
                    logger.debug(f"  ✓ Matched {current_surah}:{ayah_num} (fuzzy: {similarity:.2f})")
                else:
                    consecutive_misses += 1
                    logger.debug(f"  ✗ Missed {current_surah}:{ayah_num} (similarity: {similarity:.2f})")
                    if consecutive_misses >= max_consecutive_misses:
                        logger.info(f"Stopping after {consecutive_misses} consecutive misses")
                        break
        
        # Final coverage check
        final_coverage = matched_word_count / total_words
        logger.info(f"Final coverage: {final_coverage*100:.1f}% ({matched_word_count}/{total_words} words)")
        
        if final_coverage < min_coverage:
            logger.warning(f"Coverage {final_coverage*100:.1f}% below threshold {min_coverage*100}%")
        
        return matched_verses
    
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
    
    def _fill_backward_gaps(self, normalized_text: str, surah_num: int, start_ayah: int) -> List[Dict]:
        """
        Fill backward gaps by matching ayahs before start_ayah.
        Works backward from start_ayah-1 to ayah 1, matching verses in the text.
        """
        if start_ayah <= 1:
            return []  # No gaps to fill
        
        logger.info(f"Checking for backward gaps before ayah {start_ayah}")
        
        backward_matches = []
        
        # Try to match ayahs from start_ayah-1 down to 1
        for ayah_num in range(start_ayah - 1, 0, -1):
            verse_data = self._get_verse_by_key(surah_num, ayah_num)
            if not verse_data:
                continue
            
            verse_normalized = verse_data['normalized']
            
            # Check if this verse appears in the text
            if verse_normalized in normalized_text:
                backward_matches.insert(0, {
                    'surah': surah_num,
                    'ayah': ayah_num,
                    'text': verse_data['text'],
                    'similarity': 1.0
                })
                logger.info(f"  ✓ Found backward match: {surah_num}:{ayah_num} (exact)")
            else:
                # Try fuzzy match
                similarity = fuzz.partial_ratio(verse_normalized, normalized_text) / 100.0
                if similarity >= 0.75:
                    backward_matches.insert(0, {
                        'surah': surah_num,
                        'ayah': ayah_num,
                        'text': verse_data['text'],
                        'similarity': similarity
                    })
                    logger.info(f"  ✓ Found backward match: {surah_num}:{ayah_num} (fuzzy: {similarity:.2f})")
                else:
                    # Stop if we can't match - don't want to add incorrect verses
                    logger.debug(f"  ✗ Stopped backward fill at ayah {ayah_num} (similarity: {similarity:.2f})")
                    break
        
        return backward_matches
    
    def _find_surah_by_constraint_propagation(self, text_words: List[str], max_batches: int = 5) -> Tuple[Optional[int], Optional[int]]:
        """
        Use constraint propagation to determine the surah and starting ayah.
        Searches multiple batches and intersects results to narrow down possibilities.
        
        Returns:
            Tuple of (surah_number, start_ayah_number) or (None, None) if not found
        """
        if not PYQURAN_AVAILABLE or not pyquran:
            return None, None
        
        # Collect candidates from multiple batches
        all_candidates = []
        batch_size = 5  # words per batch
        
        for batch_idx in range(min(max_batches, len(text_words) // batch_size)):
            start_idx = batch_idx * batch_size
            end_idx = start_idx + batch_size
            batch_words = text_words[start_idx:end_idx]
            
            # Try different word counts within this batch
            batch_candidates = []
            for word_count in [1, 2, 3, 4, 5]:
                if len(batch_words) >= word_count:
                    search_text = ' '.join(batch_words[:word_count])
                    
                    try:
                        results = pyquran.search_sequence(sequancesList=[search_text], mode=3)
                        
                        if results and search_text in results:
                            matches = results[search_text]
                            # Collect all matches with position==0 (verse starts with this)
                            for matched_text, position, verse_num, chapter_num in matches:
                                if position == 0:
                                    batch_candidates.append({
                                        'surah': chapter_num,
                                        'ayah': verse_num,
                                        'batch_idx': batch_idx,
                                        'text': matched_text
                                    })
                    except:
                        continue
            
            if batch_candidates:
                all_candidates.append(batch_candidates)
                logger.info(f"Batch {batch_idx}: Found {len(batch_candidates)} candidates")
        
        if not all_candidates:
            logger.warning("No candidates found in any batch")
            return None, None
        
        # Constraint propagation: intersect candidates
        logger.info(f"Starting constraint propagation with {len(all_candidates)} batches")
        
        # Start with first batch candidates
        possible_sequences = []
        for candidate in all_candidates[0]:
            possible_sequences.append([candidate])
        
        # For each subsequent batch, try to extend sequences
        for batch_idx in range(1, len(all_candidates)):
            new_sequences = []
            
            for sequence in possible_sequences:
                last_match = sequence[-1]
                expected_surah = last_match['surah']
                expected_ayah_min = last_match['ayah']
                expected_ayah_max = last_match['ayah'] + 5  # Allow up to 5 ayahs gap
                
                # Try to find a match in current batch that continues this sequence
                for candidate in all_candidates[batch_idx]:
                    # Check if this candidate is from the same surah and consecutive/repeated ayah
                    if candidate['surah'] == expected_surah:
                        if expected_ayah_min <= candidate['ayah'] <= expected_ayah_max:
                            # Valid continuation
                            new_sequence = sequence + [candidate]
                            new_sequences.append(new_sequence)
            
            if new_sequences:
                possible_sequences = new_sequences
                logger.info(f"After batch {batch_idx}: {len(possible_sequences)} possible sequences")
            else:
                logger.warning(f"No valid sequences after batch {batch_idx}, keeping previous")
                break
        
        if not possible_sequences:
            logger.warning("No valid sequences found")
            return None, None
        
        # Pick the longest/best sequence
        best_sequence = max(possible_sequences, key=len)
        surah_num = best_sequence[0]['surah']
        start_ayah = best_sequence[0]['ayah']
        
        logger.info(f"✓ Constraint propagation result: Surah {surah_num}, Ayah {start_ayah} ({len(best_sequence)} batches matched)")
        
        return surah_num, start_ayah
    
    def _get_verse_by_key(self, surah: int, ayah: int) -> Optional[Dict]:
        """
        Get verse data by surah and ayah number.
        """
        for verse in self.quran_data:
            if verse['surah'] == surah and verse['ayah'] == ayah:
                return verse
        return None
    
    def _search_verse_with_pyquran(self, text: str) -> Optional[Dict]:
        """
        Search for a verse using pyquran's search_sequence function.
        Mode 3: search without tashkeel, return with tashkeel.
        Tries progressively shorter sequences if longer ones fail.
        """
        if not PYQURAN_AVAILABLE or not pyquran:
            return None
        
        try:
            words = text.split()
            
            # Try different word counts: start with shorter sequences for first ayah detection
            for word_count in [1, 2, 3, 5, 7]:
                if len(words) >= word_count:
                    search_text = ' '.join(words[:word_count])
                    
                    try:
                        # Use mode 3: search without tashkeel, return with tashkeel
                        results = pyquran.search_sequence(
                            sequancesList=[search_text],
                            mode=3
                        )
                        
                        if results and search_text in results:
                            matches = results[search_text]
                            if matches:
                                # Get first match where position==0 (verse starts with this text)
                                # This avoids matching words in the middle of verses
                                for matched_text, position, verse_num, chapter_num in matches:
                                    if position == 0:  # Verse starts with this text
                                        logger.info(f"PyQuran found match with {word_count} words: Surah {chapter_num}:{verse_num}")
                                        
                                        return {
                                            'surah': chapter_num,
                                            'ayah': verse_num,
                                            'text': matched_text,
                                            'similarity': 1.0  # Exact match from search
                                        }
                                
                                # If no position==0 match, take first match
                                matched_text, position, verse_num, chapter_num = matches[0]
                                logger.info(f"PyQuran found match with {word_count} words: Surah {chapter_num}:{verse_num} (pos={position})")
                                
                                return {
                                    'surah': chapter_num,
                                    'ayah': verse_num,
                                    'text': matched_text,
                                    'similarity': 1.0
                                }
                    except Exception as e:
                        logger.debug(f"PyQuran search with {word_count} words failed: {e}")
                        continue
                        
        except Exception as e:
            logger.debug(f"PyQuran search failed: {e}")
        
        return None
    
    def _find_best_verse_match(self, text: str, min_similarity: float = 0.6) -> Optional[Dict]:
        """
        Find the best matching verse for given text using fuzzy string matching.
        Uses rapidfuzz for fast similarity calculation with multiple strategies.
        """
        best_score = 0
        best_verse = None
        
        # Strategy 1: Try exact beginning match (first 3-5 words)
        text_words = text.split()
        if len(text_words) >= 3:
            # Try matching first 3, 4, and 5 words
            for word_count in [5, 4, 3]:
                if len(text_words) >= word_count:
                    search_prefix = ' '.join(text_words[:word_count])
                    
                    for verse in self.quran_data:
                        verse_words = verse['normalized'].split()
                        if len(verse_words) >= word_count:
                            verse_prefix = ' '.join(verse_words[:word_count])
                            
                            # Check if prefixes match closely
                            prefix_similarity = fuzz.ratio(search_prefix, verse_prefix) / 100.0
                            
                            if prefix_similarity >= 0.85:  # High threshold for prefix match
                                # Found a strong prefix match, check full similarity
                                full_similarity = fuzz.partial_ratio(text, verse['normalized']) / 100.0
                                
                                if full_similarity > best_score:
                                    best_score = full_similarity
                                    best_verse = verse
                                    print(f"  → Prefix match: Surah {verse['surah']}:{verse['ayah']} (score: {full_similarity:.2f})")
        
        # Strategy 2: If no good prefix match, try full fuzzy matching
        if best_score < 0.7:
            for verse in self.quran_data:
                # Use partial_ratio for better substring matching
                similarity = fuzz.partial_ratio(text, verse['normalized']) / 100.0
                
                # Boost score if text contains verse or vice versa
                if text in verse['normalized'] or verse['normalized'] in text:
                    similarity = max(similarity, 0.85)
                
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
