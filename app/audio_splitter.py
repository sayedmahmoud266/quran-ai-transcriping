"""
Audio splitting module for extracting individual ayahs from audio files.
"""

import os
import io
import json
import zipfile
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioSplitter:
    """Handles splitting audio files into individual ayah segments."""
    
    def __init__(self):
        """Initialize the audio splitter."""
        pass
    
    def _parse_timestamp(self, timestamp: str) -> int:
        """
        Convert timestamp string (HH:MM:SS.mmm) to milliseconds.
        
        Args:
            timestamp: Timestamp in format "HH:MM:SS.mmm"
            
        Returns:
            Time in milliseconds
        """
        try:
            # Split into time and milliseconds
            time_part, ms_part = timestamp.split('.')
            hours, minutes, seconds = map(int, time_part.split(':'))
            milliseconds = int(ms_part)
            
            # Convert to total milliseconds
            total_ms = (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
            return total_ms
        except Exception as e:
            logger.error(f"Error parsing timestamp '{timestamp}': {e}")
            return 0
    
    def _detect_silence_gaps_in_segment(
        self,
        segment: AudioSegment,
        ayah_text_normalized: str,
        ayah_start_time_ms: int,
        word_timestamps: List[Dict] = None,
        threshold_ms: int = 500
    ) -> List[Dict]:
        """
        Detect silence gaps within an ayah segment (excluding leading/trailing silences).
        
        Args:
            segment: Audio segment for the ayah
            ayah_text_normalized: Normalized ayah text
            ayah_start_time_ms: Start time of ayah in absolute milliseconds
            word_timestamps: Word-level timestamps from transcription
            threshold_ms: Minimum silence duration to detect (milliseconds)
            
        Returns:
            List of silence gap dictionaries (only internal gaps)
        """
        silence_gaps = []
        
        try:
            # Detect silence in the segment
            from pydub.silence import detect_silence
            
            # Detect silences longer than threshold_ms with -40dBFS threshold
            silences = detect_silence(
                segment,
                min_silence_len=threshold_ms,
                silence_thresh=-40
            )
            
            if not silences:
                return []
            
            # Calculate word count
            ayah_words = ayah_text_normalized.split()
            word_count = len(ayah_words)
            segment_duration_ms = len(segment)
            
            # Define margins to exclude leading/trailing silences
            # Consider first/last 10% of audio as edge regions
            leading_margin = segment_duration_ms * 0.1
            trailing_margin = segment_duration_ms * 0.9
            
            # Process each silence, excluding those at edges
            for silence_start, silence_end in silences:
                # Skip silences that are at the very beginning or end
                if silence_start < leading_margin:
                    logger.debug(f"Skipping leading silence at {silence_start}ms")
                    continue
                
                if silence_end > trailing_margin:
                    logger.debug(f"Skipping trailing silence at {silence_end}ms")
                    continue
                
                silence_duration = silence_end - silence_start
                
                # Calculate absolute silence time
                absolute_silence_start = ayah_start_time_ms + silence_start
                
                logger.info(f"=== Silence Detection Debug ===")
                logger.info(f"Ayah start time (absolute): {ayah_start_time_ms}ms")
                logger.info(f"Silence start (relative): {silence_start}ms")
                logger.info(f"Silence start (absolute): {absolute_silence_start}ms")
                logger.info(f"Ayah text: {ayah_text_normalized}")
                logger.info(f"Ayah words: {ayah_words}")
                logger.info(f"Ayah word count: {word_count}")
                
                # Find word position using actual timestamps if available
                word_position = None
                if word_timestamps:
                    logger.info(f"Total word timestamps available: {len(word_timestamps)}")
                    
                    # Filter timestamps to only those within this ayah's time range
                    ayah_end_time_ms = ayah_start_time_ms + segment_duration_ms
                    ayah_word_timestamps = []
                    
                    for wt in word_timestamps:
                        word_start_ms = int(wt['start'] * 1000)
                        word_end_ms = int(wt['end'] * 1000)
                        
                        # Check if this word is within the ayah's time range
                        if word_start_ms >= ayah_start_time_ms and word_end_ms <= ayah_end_time_ms:
                            ayah_word_timestamps.append(wt)
                    
                    logger.info(f"Words within this ayah's time range: {len(ayah_word_timestamps)}")
                    logger.info(f"First 5 ayah words with timestamps:")
                    for i, wt in enumerate(ayah_word_timestamps[:5]):
                        logger.info(f"  Ayah word {i+1}: '{wt.get('word', 'N/A')}' @ {wt['start']:.3f}s - {wt['end']:.3f}s ({int(wt['end']*1000)}ms)")
                    
                    # Find which word within THIS AYAH the silence comes after
                    for word_idx, word_ts in enumerate(ayah_word_timestamps):
                        word_end_ms = int(word_ts['end'] * 1000)
                        word_text = word_ts.get('word', 'N/A')
                        
                        # If silence starts after this word ends
                        if word_end_ms <= absolute_silence_start:
                            word_position = word_idx + 1  # Position after this word (1-indexed within ayah)
                            logger.debug(f"  Ayah word {word_idx+1} ('{word_text}') ends at {word_end_ms}ms <= {absolute_silence_start}ms")
                        else:
                            logger.info(f"  Silence comes after ayah word {word_position}: before '{word_text}' @ {word_end_ms}ms")
                            break
                else:
                    logger.warning("No word timestamps available, using time-based estimation")
                
                # Fallback to time-based estimation if timestamps not available
                if word_position is None:
                    position_ratio = silence_start / segment_duration_ms
                    word_position = int(position_ratio * word_count)
                    if word_position <= 0:
                        word_position = 1
                    if word_position >= word_count:
                        word_position = word_count - 1
                
                # Ensure position is within bounds
                if word_position <= 0:
                    word_position = 1
                if word_position >= word_count:
                    word_position = word_count - 1
                
                # Log final result
                if word_position and word_position <= len(ayah_words):
                    logger.info(f"✓ Final result: Silence after word {word_position}: '{ayah_words[word_position-1]}'")
                else:
                    logger.info(f"✓ Final result: Silence after word {word_position}")
                logger.info(f"==============================\n")
                
                silence_gaps.append({
                    "silence_start_ms": silence_start,
                    "silence_end_ms": silence_end,
                    "silence_duration_ms": silence_duration,
                    "silence_position_after_word": word_position
                })
            
            if silence_gaps:
                logger.debug(f"Detected {len(silence_gaps)} internal silence gaps in ayah")
            
        except Exception as e:
            logger.warning(f"Error detecting silence gaps: {e}")
        
        return silence_gaps
    
    def _find_best_split_point(
        self,
        audio: AudioSegment,
        ayah1_details: Dict,
        ayah2_details: Dict,
        original_split_ms: int
    ) -> Tuple[int, bool]:
        """
        Find the best split point between two consecutive ayahs with 0ms gap.
        Uses silence detection and duration verification.
        
        Args:
            audio: Full audio segment
            ayah1_details: First ayah details
            ayah2_details: Second ayah details
            original_split_ms: Original split point in milliseconds
            
        Returns:
            Tuple of (best_split_point_ms, is_confident)
        """
        from pydub.silence import detect_silence
        from app.quran_data import quran_data
        
        logger.info(f"🔍 Finding best split point between ayah {ayah1_details['ayah_number']} and {ayah2_details['ayah_number']}")
        
        # Get ayah 1 expected duration
        ayah1_start = self._parse_timestamp(ayah1_details['audio_start_timestamp'])
        ayah1_end = self._parse_timestamp(ayah1_details['audio_end_timestamp'])
        expected_duration = ayah1_end - ayah1_start
        
        # Define search window (±30 seconds around original split)
        search_start = max(ayah1_start, original_split_ms - 30000)
        search_end = min(len(audio), original_split_ms + 30000)
        search_segment = audio[search_start:search_end]
        
        logger.info(f"  Search window: {search_start}ms to {search_end}ms")
        
        # Detect all silences in the search window
        silences = detect_silence(
            search_segment,
            min_silence_len=300,  # 300ms minimum
            silence_thresh=-40
        )
        
        if not silences:
            logger.warning("  ⚠ No silences detected in search window, keeping original split")
            return original_split_ms, False
        
        logger.info(f"  Found {len(silences)} silence points")
        
        # Try each silence point
        best_split = original_split_ms
        best_confidence = False
        best_ratio = 999
        
        for silence_start, silence_end in silences:
            # Convert to absolute position (use end of silence as split point)
            test_split = search_start + silence_end
            
            # Calculate ayah 1 duration with this split
            test_duration = test_split - ayah1_start
            duration_ratio = abs(test_duration - expected_duration) / expected_duration if expected_duration > 0 else 999
            
            logger.debug(f"    Split at {test_split}ms: duration {test_duration}ms (expected {expected_duration}ms), ratio {duration_ratio:.2f}")
            
            # Check if duration is reasonable (within 15% of expected)
            if duration_ratio < 0.15 and duration_ratio < best_ratio:
                logger.info(f"    ✓ Good match! Duration ratio: {duration_ratio:.2f}")
                best_split = test_split
                best_confidence = True
                best_ratio = duration_ratio
        
        if best_confidence:
            logger.info(f"  ✅ Found confident split point at {best_split}ms (ratio: {best_ratio:.2f})")
        else:
            logger.warning(f"  ⚠ No confident split found, using original at {original_split_ms}ms")
            best_split = original_split_ms
        
        return best_split, best_confidence
    
    def _calculate_adjusted_timestamps(
        self,
        ayah_details: List[Dict],
        audio: AudioSegment = None
    ) -> List[Tuple[int, int, bool]]:
        """
        Calculate adjusted timestamps by splitting gaps between ayahs.
        For consecutive ayahs with 0ms gap, uses intelligent split point detection.
        
        Args:
            ayah_details: List of ayah details with timestamps
            audio: Optional full audio for intelligent split detection
            
        Returns:
            List of (adjusted_start_ms, adjusted_end_ms, is_uncertain) tuples
        """
        adjusted_timestamps = []
        
        for idx, detail in enumerate(ayah_details):
            start_time = self._parse_timestamp(detail['audio_start_timestamp'])
            end_time = self._parse_timestamp(detail['audio_end_timestamp'])
            is_uncertain = False
            
            # Adjust start time (split gap with previous ayah)
            if idx > 0:
                prev_end = self._parse_timestamp(ayah_details[idx - 1]['audio_end_timestamp'])
                gap = start_time - prev_end
                
                if gap == 0 and audio is not None:
                    # Zero gap - use intelligent split detection
                    logger.info(f"⚠ Zero gap detected between ayah {ayah_details[idx-1]['ayah_number']} and {detail['ayah_number']}")
                    best_split, is_confident = self._find_best_split_point(
                        audio,
                        ayah_details[idx - 1],
                        detail,
                        start_time  # Original split point
                    )
                    
                    # Update previous ayah's end time
                    if idx > 0 and len(adjusted_timestamps) > 0:
                        prev_start, _, prev_uncertain = adjusted_timestamps[idx - 1]
                        adjusted_timestamps[idx - 1] = (prev_start, best_split, not is_confident)
                    
                    adjusted_start = best_split
                    is_uncertain = not is_confident
                    
                elif gap > 0:
                    # Normal gap - split in the middle
                    adjusted_start = prev_end + (gap // 2)
                else:
                    # Negative gap (overlap) - use original
                    adjusted_start = start_time
                    is_uncertain = True
            else:
                # First ayah - use original start time
                adjusted_start = start_time
            
            # Adjust end time (split gap with next ayah)
            if idx < len(ayah_details) - 1:
                next_start = self._parse_timestamp(ayah_details[idx + 1]['audio_start_timestamp'])
                gap = next_start - end_time
                
                if gap == 0:
                    # Will be handled when processing next ayah
                    adjusted_end = end_time
                elif gap > 0:
                    # Split the gap in the middle
                    adjusted_end = end_time + (gap // 2)
                else:
                    adjusted_end = end_time
            else:
                # Last ayah - use original end time
                adjusted_end = end_time
            
            adjusted_timestamps.append((adjusted_start, adjusted_end, is_uncertain))
            
            uncertain_flag = " [UNCERTAIN]" if is_uncertain else ""
            logger.debug(f"Ayah {idx+1}: Original [{start_time}-{end_time}] → Adjusted [{adjusted_start}-{adjusted_end}]{uncertain_flag}")
        
        return adjusted_timestamps
    
    def split_audio_by_ayahs(
        self,
        audio_file_path: str,
        ayah_details: List[Dict],
        word_timestamps: List[Dict] = None
    ) -> Tuple[io.BytesIO, str]:
        """
        Split audio file into individual ayah segments and create a zip file.
        
        Args:
            audio_file_path: Path to the original audio file
            ayah_details: List of ayah details with timestamps
            word_timestamps: Optional word-level timestamps from transcription
            
        Returns:
            Tuple of (BytesIO object containing zip file, suggested filename)
        """
        try:
            # Load the original audio file
            file_ext = Path(audio_file_path).suffix.lower()
            logger.info(f"Loading audio file: {audio_file_path} (format: {file_ext})")
            
            # Load audio based on format
            if file_ext == '.mp3':
                audio = AudioSegment.from_mp3(audio_file_path)
            elif file_ext == '.wav':
                audio = AudioSegment.from_wav(audio_file_path)
            elif file_ext == '.m4a':
                audio = AudioSegment.from_file(audio_file_path, format='m4a')
            elif file_ext == '.ogg':
                audio = AudioSegment.from_ogg(audio_file_path)
            elif file_ext == '.flac':
                audio = AudioSegment.from_file(audio_file_path, format='flac')
            else:
                # Try generic loader
                audio = AudioSegment.from_file(audio_file_path)
            
            logger.info(f"Audio loaded: duration={len(audio)/1000:.2f}s, channels={audio.channels}, sample_rate={audio.frame_rate}Hz")
            
            # Calculate adjusted timestamps (split gaps between ayahs, with intelligent split detection)
            adjusted_timestamps = self._calculate_adjusted_timestamps(ayah_details, audio)
            
            # Create a BytesIO object to store the zip file
            zip_buffer = io.BytesIO()
            
            # Determine surah number from first ayah (excluding basmala)
            surah_num = None
            for detail in ayah_details:
                if not detail.get('is_basmala', False):
                    surah_num = detail['surah_number']
                    break
            
            if not surah_num and ayah_details:
                surah_num = ayah_details[0]['surah_number']
            
            # Prepare metadata for JSON file
            ayah_metadata = []
            
            # Create zip file
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                logger.info(f"Creating zip file with {len(ayah_details)} ayahs")
                
                for idx, detail in enumerate(ayah_details):
                    try:
                        # Get adjusted timestamps and uncertainty flag
                        start_time, end_time, is_uncertain = adjusted_timestamps[idx]
                        
                        # Extract segment
                        segment = audio[start_time:end_time]
                        
                        # Generate filename
                        surah = detail['surah_number']
                        ayah = detail['ayah_number']
                        is_basmala = detail.get('is_basmala', False)
                        ayah_text = detail.get('ayah_text_tashkeel', '')
                        
                        if is_basmala:
                            # Basmala as ayah 000 to sort first
                            filename = f"surah_{surah:03d}_ayah_000_basmala{file_ext}"
                            ayah_number_for_metadata = 0
                        else:
                            filename = f"surah_{surah:03d}_ayah_{ayah:03d}{file_ext}"
                            ayah_number_for_metadata = ayah
                        
                        # Export segment to BytesIO
                        segment_buffer = io.BytesIO()
                        
                        # Export based on format
                        if file_ext == '.mp3':
                            segment.export(segment_buffer, format='mp3', bitrate='192k')
                        elif file_ext == '.wav':
                            segment.export(segment_buffer, format='wav')
                        elif file_ext == '.m4a':
                            segment.export(segment_buffer, format='ipod')
                        elif file_ext == '.ogg':
                            segment.export(segment_buffer, format='ogg')
                        elif file_ext == '.flac':
                            segment.export(segment_buffer, format='flac')
                        else:
                            # Default to wav for unknown formats
                            segment.export(segment_buffer, format='wav')
                            filename = filename.replace(file_ext, '.wav')
                        
                        # Add to zip
                        zip_file.writestr(filename, segment_buffer.getvalue())
                        
                        # Normalize text (without tashkeel)
                        from app.quran_data import quran_data
                        ayah_text_normalized = quran_data.normalize_arabic_text(ayah_text)
                        
                        # Calculate actual audio offsets (without gap adjustments)
                        original_start = self._parse_timestamp(detail['audio_start_timestamp'])
                        original_end = self._parse_timestamp(detail['audio_end_timestamp'])
                        
                        # Detect silence gaps within the ayah
                        silence_gaps = self._detect_silence_gaps_in_segment(
                            segment,
                            ayah_text_normalized,
                            start_time,  # Absolute start time for word matching
                            word_timestamps,
                            threshold_ms=500  # 500ms minimum silence
                        )
                        
                        # Calculate relative offsets (within the extracted segment)
                        # Relative start: how many ms from the beginning of the file to the actual ayah start
                        relative_actual_start = original_start - start_time
                        
                        # Relative end: NEGATIVE number showing how many ms removed from the end
                        # If original_end < end_time, the ayah was cut short
                        relative_actual_end = original_end - end_time  # Will be negative if cut off
                        
                        # Log if ayah was cut off
                        if relative_actual_end < -1000:  # More than 1 second cut off
                            logger.warning(f"Ayah {detail['ayah_number']} was cut off: {-relative_actual_end}ms removed from end")
                        
                        # Build metadata entry with unified schema
                        metadata_entry = {
                            "surah_number": surah,
                            "ayah_number": ayah_number_for_metadata,
                            "ayah_text": ayah_text,
                            "ayah_text_normalized": ayah_text_normalized,
                            "filename": filename,
                            "is_basmala": is_basmala,
                            "duration_seconds": round(len(segment) / 1000, 2),
                            # Absolute offsets (relative to entire surah audio)
                            "audio_start_offset_absolute_ms": start_time,
                            "audio_end_offset_absolute_ms": end_time,
                            "actual_ayah_start_offset_absolute_ms": original_start,
                            "actual_ayah_end_offset_absolute_ms": original_end,
                            # Relative offsets (within this ayah's audio file)
                            "actual_ayah_start_offset_relative_ms": relative_actual_start,
                            "actual_ayah_end_offset_relative_ms": relative_actual_end,
                            # Silence gaps (always present, empty array if none detected)
                            "silence_gaps": silence_gaps if silence_gaps else [],
                            # Split point uncertainty flag
                            "split_point_uncertain": is_uncertain
                        }
                        
                        ayah_metadata.append(metadata_entry)
                        
                        logger.debug(f"Added {filename} to zip (duration: {len(segment)/1000:.2f}s)")
                        
                    except Exception as e:
                        logger.error(f"Error processing ayah {idx+1}: {e}")
                        continue
                
                # Add metadata JSON file
                metadata_json = {
                    "surah_number": surah_num,
                    "total_ayahs": len(ayah_details),
                    "audio_format": file_ext.replace('.', ''),
                    "ayahs": ayah_metadata
                }
                
                zip_file.writestr(
                    'metadata.json',
                    json.dumps(metadata_json, ensure_ascii=False, indent=2)
                )
                logger.info("Added metadata.json to zip")
                
                # Add a README file
                readme_content = f"""Quran Audio Ayah Segments
========================

Surah: {surah_num}
Total Ayahs: {len(ayah_details)}
Format: {file_ext}

Files are named as:
- surah_XXX_ayah_000_basmala{file_ext} (for Basmala - always first)
- surah_XXX_ayah_YYY{file_ext} (for regular ayahs)

Where:
- XXX = Surah number (3 digits, zero-padded)
- YYY = Ayah number (3 digits, zero-padded)

Additional Files:
- metadata.json: Contains ayah text, numbers, and filenames

Audio Enhancement:
- Gaps between ayahs are split in the middle
- Each ayah includes half of the silence before and after it
- This ensures smooth playback without cutting off audio

Generated by Quran AI Transcription API v2.1.0
https://github.com/sayedmahmoud266/quran-ai-transcriping
"""
                zip_file.writestr('README.txt', readme_content)
            
            # Reset buffer position
            zip_buffer.seek(0)
            
            # Generate suggested filename
            zip_filename = f"surah_{surah_num:03d}_ayahs.zip"
            
            logger.info(f"Zip file created successfully: {zip_filename}")
            
            return zip_buffer, zip_filename
            
        except Exception as e:
            logger.error(f"Error splitting audio: {e}")
            raise


# Create singleton instance
audio_splitter = AudioSplitter()
