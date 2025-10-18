"""
Audio splitting module for splitting audio by ayahs.
"""

import io
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from pydub import AudioSegment
from pydub.silence import detect_silence
import zipfile

logger = logging.getLogger(__name__)

# Global debug recorder (set by background worker)
_debug_recorder = None

def set_debug_recorder(recorder):
    """Set the global debug recorder."""
    global _debug_recorder
    _debug_recorder = recorder


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
        threshold_ms: int = 500
    ) -> List[Dict]:
        """
        Detect silence gaps within an ayah segment (excluding leading/trailing silences).
        
        Args:
            segment: Audio segment for the ayah
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
                
                silence_gaps.append({
                    "silence_start_ms": silence_start,
                    "silence_end_ms": silence_end,
                    "silence_duration_ms": silence_duration
                })
            
            if silence_gaps:
                logger.debug(f"Detected {len(silence_gaps)} internal silence gaps in ayah")
            
        except Exception as e:
            logger.warning(f"Error detecting silence gaps: {e}")
        
        return silence_gaps
    
    def _find_silence_near_cutoff(
        self,
        audio: AudioSegment,
        cutoff_point_ms: int,
        search_window_ms: int = 10000
    ) -> Optional[int]:
        """
        Search for silence gaps near a cutoff point.
        
        Args:
            audio: Full audio segment
            cutoff_point_ms: The cutoff point to search around
            search_window_ms: How many ms to search before and after (default 10s)
            
        Returns:
            Midpoint of closest silence gap, or None if no silence found
        """
        from pydub.silence import detect_silence
        
        # Define search region
        search_start = max(0, cutoff_point_ms - search_window_ms)
        search_end = min(len(audio), cutoff_point_ms + search_window_ms)
        
        # Extract the search segment
        search_segment = audio[search_start:search_end]
        
        logger.info(f"  Searching for silence around {cutoff_point_ms}ms (±{search_window_ms}ms)")
        
        # Detect silences in this segment
        silences = detect_silence(
            search_segment,
            min_silence_len=500,  # 500ms minimum silence
            silence_thresh=-40    # -40 dBFS threshold
        )
        
        if not silences:
            logger.warning(f"  No silence found in search window")
            return None
        
        # Find the silence closest to the cutoff point
        # Silences are relative to search_segment, so adjust to absolute time
        closest_silence = None
        min_distance = float('inf')
        
        for silence_start, silence_end in silences:
            # Convert to absolute time
            abs_silence_start = search_start + silence_start
            abs_silence_end = search_start + silence_end
            silence_midpoint = (abs_silence_start + abs_silence_end) // 2
            
            # Calculate distance from cutoff point
            distance = abs(silence_midpoint - cutoff_point_ms)
            
            if distance < min_distance:
                min_distance = distance
                closest_silence = silence_midpoint
        
        if closest_silence:
            logger.info(f"  ✓ Found silence at {closest_silence}ms (distance: {min_distance}ms from cutoff)")
        
        return closest_silence
    
    def _calculate_adjusted_timestamps(
        self,
        ayah_details: List[Dict],
        audio: AudioSegment = None
    ) -> List[Tuple[int, int, bool]]:
        """
        Calculate adjusted timestamps by splitting gaps between ayahs.
        Uses intelligent gap detection when consecutive ayahs have 0ms gaps.
        
        Args:
            ayah_details: List of ayah details with timestamps
            audio: Optional audio segment for silence detection
            
        Returns:
            List of (adjusted_start_ms, adjusted_end_ms, uncertain_flag) tuples
        """
        adjusted_timestamps = []
        
        for idx, detail in enumerate(ayah_details):
            start_time = self._parse_timestamp(detail['audio_start_timestamp'])
            end_time = self._parse_timestamp(detail['audio_end_timestamp'])
            uncertain = False
            
            # Adjust start time (split gap with previous ayah)
            if idx > 0:
                prev_end = self._parse_timestamp(ayah_details[idx - 1]['audio_end_timestamp'])
                gap = start_time - prev_end
                
                if gap == 0 and audio is not None:
                    # INTELLIGENT GAP DETECTION: 0ms gap detected!
                    logger.warning(f"⚠ Ayah {idx+1}: 0ms gap detected with previous ayah!")
                    logger.info(f"  Performing secondary silence search around cutoff point {start_time}ms")
                    
                    # Search for silence near the cutoff point
                    silence_midpoint = self._find_silence_near_cutoff(audio, start_time, search_window_ms=10000)
                    
                    if silence_midpoint:
                        # Use the silence midpoint as the new split
                        adjusted_start = silence_midpoint
                        # Also update the previous ayah's end time
                        if adjusted_timestamps:
                            prev_start, prev_end, prev_uncertain = adjusted_timestamps[-1]
                            adjusted_timestamps[-1] = (prev_start, silence_midpoint, prev_uncertain)
                        logger.info(f"  ✓ Adjusted split point to {silence_midpoint}ms (silence-based)")
                    else:
                        # No silence found - use original but mark as uncertain
                        adjusted_start = start_time
                        uncertain = True
                        logger.warning(f"  ✗ No silence found - using original cutoff (UNCERTAIN)")
                
                elif gap > 0:
                    # Normal gap - split in the middle
                    adjusted_start = prev_end + (gap // 2)
                else:
                    # Negative gap (overlap) - use original
                    adjusted_start = start_time
            else:
                # First ayah - use original start time
                adjusted_start = start_time
            
            # Adjust end time (split gap with next ayah)
            if idx < len(ayah_details) - 1:
                next_start = self._parse_timestamp(ayah_details[idx + 1]['audio_start_timestamp'])
                gap = next_start - end_time
                
                if gap == 0 and audio is not None:
                    # This will be handled when processing the next ayah
                    adjusted_end = end_time
                elif gap > 0:
                    # Normal gap - split in the middle
                    adjusted_end = end_time + (gap // 2)
                else:
                    # Negative gap (overlap) - use original
                    adjusted_end = end_time
            else:
                # Last ayah - use original end time
                adjusted_end = end_time
            
            adjusted_timestamps.append((adjusted_start, adjusted_end, uncertain))
            
            uncertainty_flag = " [UNCERTAIN]" if uncertain else ""
            logger.debug(f"Ayah {idx+1}: Original [{start_time}-{end_time}] → Adjusted [{adjusted_start}-{adjusted_end}]{uncertainty_flag}")
        
        return adjusted_timestamps
    
    def _create_zip_with_timestamps(
        self,
        audio: AudioSegment,
        ayah_details: List[Dict],
        timestamps_list: List[Tuple],
        file_ext: str,
        surah_num: int
    ) -> Tuple[io.BytesIO, List[Dict]]:
        """
        Helper method to create a zip file with given timestamps.
        
        Args:
            audio: Loaded audio segment
            ayah_details: List of ayah details
            timestamps_list: List of (start_ms, end_ms, uncertain_flag) tuples
            file_ext: File extension
            surah_num: Surah number
            
        Returns:
            Tuple of (zip_buffer, ayah_metadata)
        """
        zip_buffer = io.BytesIO()
        ayah_metadata = []
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            logger.info(f"Creating zip file with {len(ayah_details)} ayahs")
            
            for idx, detail in enumerate(ayah_details):
                try:
                    # Get timestamps (with uncertainty flag)
                    timestamp_tuple = timestamps_list[idx]
                    if len(timestamp_tuple) == 3:
                        start_time, end_time, uncertain = timestamp_tuple
                    else:
                        start_time, end_time = timestamp_tuple
                        uncertain = False
                    
                    # Extract segment
                    segment = audio[start_time:end_time]
                    
                    # Generate filename
                    surah = detail['surah_number']
                    ayah = detail['ayah_number']
                    is_basmala = detail.get('is_basmala', False)
                    ayah_text = detail.get('ayah_text_tashkeel', '')
                    
                    if is_basmala:
                        filename = f"surah_{surah:03d}_ayah_000_basmala{file_ext}"
                        ayah_number_for_metadata = 0
                    else:
                        filename = f"surah_{surah:03d}_ayah_{ayah:03d}{file_ext}"
                        ayah_number_for_metadata = ayah
                    
                    # Export segment
                    segment_buffer = io.BytesIO()
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
                        segment.export(segment_buffer, format='wav')
                        filename = filename.replace(file_ext, '.wav')
                    
                    zip_file.writestr(filename, segment_buffer.getvalue())
                    
                    # Normalize text (basic normalization)
                    import re
                    # Remove diacritics and normalize
                    ayah_text_normalized = re.sub(r'[\u064B-\u065F\u0670\u0610-\u061A\u06D6-\u06ED]', '', ayah_text)
                    ayah_text_normalized = ayah_text_normalized.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
                    ayah_text_normalized = ayah_text_normalized.replace('ة', 'ه')
                    ayah_text_normalized = ' '.join(ayah_text_normalized.split())
                    
                    # Calculate original timestamps
                    original_start = self._parse_timestamp(detail['audio_start_timestamp'])
                    original_end = self._parse_timestamp(detail['audio_end_timestamp'])
                    
                    # Detect silence gaps
                    silence_gaps = self._detect_silence_gaps_in_segment(
                        segment,
                        threshold_ms=500
                    )
                    
                    # Calculate relative offsets
                    relative_actual_start = original_start - start_time
                    relative_actual_end = original_end - end_time
                    
                    # Log if ayah was cut off
                    if relative_actual_end < -1000:
                        logger.warning(f"Ayah {detail['ayah_number']} cut off: {-relative_actual_end}ms removed")
                    
                    # Build metadata matching API format
                    metadata_entry = {
                        "surah_number": surah,
                        "ayah_number": ayah_number_for_metadata,
                        "ayah_text_tashkeel": ayah_text,
                        "ayah_text_normalized": ayah_text_normalized,
                        "ayah_word_count": detail.get('ayah_word_count', len(ayah_text_normalized.split())),
                        "start_from_word": detail.get('start_from_word', 1),
                        "end_to_word": detail.get('end_to_word', len(ayah_text_normalized.split())),
                        "audio_start_timestamp": detail.get('audio_start_timestamp', '00:00:00.000'),
                        "audio_end_timestamp": detail.get('audio_end_timestamp', '00:00:00.000'),
                        "audio_start_offset_absolute_ms": original_start,
                        "audio_end_offset_absolute_ms": original_end,
                        "match_confidence": detail.get('match_confidence', 1.0),
                        "is_basmala": is_basmala,
                        "filename": filename,
                        "duration_seconds": round(len(segment) / 1000, 2),
                        "chunk_mapping": detail.get('chunk_mapping', []),
                        # Legacy fields for backward compatibility
                        "audio_start_offset_absolute_ms_legacy": start_time,
                        "audio_end_offset_absolute_ms_legacy": end_time,
                        "actual_ayah_start_offset_relative_ms": relative_actual_start,
                        "actual_ayah_end_offset_relative_ms": relative_actual_end,
                        "silence_gaps": silence_gaps if silence_gaps else [],
                        "cutoff_uncertain": uncertain
                    }
                    
                    ayah_metadata.append(metadata_entry)
                    
                    uncertainty_note = " [UNCERTAIN CUTOFF]" if uncertain else ""
                    logger.debug(f"Added {filename} (duration: {len(segment)/1000:.2f}s){uncertainty_note}")
                    
                except Exception as e:
                    logger.error(f"Error processing ayah {idx+1}: {e}")
                    continue
            
            # Add metadata JSON
            # Combine all ayah texts for transcription field
            combined_transcription = " ".join([
                detail.get('ayah_text_tashkeel', '') 
                for detail in ayah_details
            ])
            
            metadata_json = {
                "surah_number": surah_num,
                "total_ayahs": len(ayah_details),
                "transcription": combined_transcription,
                "audio_format": file_ext.replace('.', ''),
                "ayahs": ayah_metadata
            }
            
            zip_file.writestr(
                'metadata.json',
                json.dumps(metadata_json, ensure_ascii=False, indent=2)
            )
            logger.info("Added metadata.json to zip")
            
            # Add README
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
- Intelligent gap detection for consecutive ayahs
- Silence-based splitting when 0ms gaps detected
- Gaps between ayahs are split optimally

Generated by Quran AI Transcription API v2.1.0
https://github.com/sayedmahmoud266/quran-ai-transcriping
"""
            zip_file.writestr('README.txt', readme_content)
        
        zip_buffer.seek(0)
        return zip_buffer, ayah_metadata
    
    def split_audio_by_ayahs(
        self,
        audio_file_path: str,
        ayah_details: List[Dict]
    ) -> Tuple[io.BytesIO, str]:
        """
        Split audio file into individual ayah segments and create a zip file.
        Uses intelligent gap detection for optimal ayah boundaries.
        
        Args:
            audio_file_path: Path to the original audio file
            ayah_details: List of ayah details with timestamps
            
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
                audio = AudioSegment.from_file(audio_file_path)
            
            logger.info(f"Audio loaded: duration={len(audio)/1000:.2f}s, channels={audio.channels}, sample_rate={audio.frame_rate}Hz")
            
            # Determine surah number
            surah_num = None
            for detail in ayah_details:
                if not detail.get('is_basmala', False):
                    surah_num = detail['surah_number']
                    break
            if not surah_num and ayah_details:
                surah_num = ayah_details[0]['surah_number']
            
            # Debug: Save before splitting
            if _debug_recorder:
                _debug_recorder.save_step(
                    "11_before_audio_splitting",
                    data={
                        "total_ayahs": len(ayah_details),
                        "audio_duration_seconds": len(audio) / 1000,
                        "ayahs": [{
                            "surah_number": d['surah_number'],
                            "ayah_number": d['ayah_number'],
                            "audio_start_timestamp": d.get('audio_start_timestamp'),
                            "audio_end_timestamp": d.get('audio_end_timestamp')
                        } for d in ayah_details]
                    }
                )
            
            # Calculate adjusted timestamps with intelligent gap detection
            logger.info("Calculating optimal ayah boundaries...")
            adjusted_timestamps = self._calculate_adjusted_timestamps(ayah_details, audio)
            
            # Create zip file
            zip_buffer, _ = self._create_zip_with_timestamps(
                audio, ayah_details, adjusted_timestamps,
                file_ext, surah_num
            )
            
            zip_filename = f"surah_{surah_num:03d}_ayahs.zip"
            logger.info(f"Zip file created successfully: {zip_filename}")
            
            # Debug: Save after splitting
            if _debug_recorder:
                # Extract ayah audio files for debug
                import numpy as np
                audio_files = []
                for idx, detail in enumerate(ayah_details):
                    if idx < len(adjusted_timestamps):
                        start_ms, end_ms, _ = adjusted_timestamps[idx]
                        segment = audio[start_ms:end_ms]
                        
                        # Convert to numpy array
                        samples = np.array(segment.get_array_of_samples())
                        if segment.channels == 2:
                            samples = samples.reshape((-1, 2))
                            samples = samples.mean(axis=1)  # Convert to mono
                        
                        # Normalize to float32
                        samples = samples.astype(np.float32) / 32768.0
                        
                        ayah_num = detail.get('ayah_number', idx)
                        is_basmala = detail.get('is_basmala', False)
                        name = f"ayah_{ayah_num:03d}_basmala" if is_basmala else f"ayah_{ayah_num:03d}"
                        
                        audio_files.append({
                            "name": name,
                            "audio": samples
                        })
                
                _debug_recorder.save_step(
                    "12_after_audio_splitting",
                    data={
                        "total_ayahs": len(ayah_details),
                        "zip_filename": zip_filename,
                        "ayahs": [{
                            "surah_number": d['surah_number'],
                            "ayah_number": d['ayah_number'],
                            "filename": d.get('filename', 'unknown'),
                            "duration_seconds": d.get('duration_seconds', 0)
                        } for d in ayah_details]
                    },
                    audio_files=audio_files,
                    sample_rate=audio.frame_rate
                )
            
            return zip_buffer, zip_filename
            
        except Exception as e:
            logger.error(f"Error splitting audio: {e}")
            raise


# Create singleton instance
audio_splitter = AudioSplitter()


# Convenience function for direct import
def split_audio_by_ayahs(audio_file_path: str, ayah_details: List[Dict]) -> Tuple[io.BytesIO, str]:
    """
    Split audio file by ayah timestamps and create a ZIP file.
    
    Convenience wrapper around AudioSplitter.split_audio_by_ayahs().
    
    Args:
        audio_file_path: Path to the audio file
        ayah_details: List of ayah details with timestamps
        
    Returns:
        Tuple of (zip_buffer, zip_filename)
    """
    return audio_splitter.split_audio_by_ayahs(audio_file_path, ayah_details)
