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
                
                # Find word position using actual timestamps if available
                word_position = None
                if word_timestamps:
                    # Find which word this silence comes after
                    for word_idx, word_ts in enumerate(word_timestamps):
                        word_end_ms = int(word_ts['end'] * 1000)
                        
                        # If silence starts after this word ends
                        if word_end_ms <= absolute_silence_start:
                            word_position = word_idx + 1  # Position after this word (1-indexed)
                        else:
                            break
                
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
    
    def _calculate_adjusted_timestamps(
        self,
        ayah_details: List[Dict]
    ) -> List[Tuple[int, int]]:
        """
        Calculate adjusted timestamps by splitting gaps between ayahs.
        
        Args:
            ayah_details: List of ayah details with timestamps
            
        Returns:
            List of (adjusted_start_ms, adjusted_end_ms) tuples
        """
        adjusted_timestamps = []
        
        for idx, detail in enumerate(ayah_details):
            start_time = self._parse_timestamp(detail['audio_start_timestamp'])
            end_time = self._parse_timestamp(detail['audio_end_timestamp'])
            
            # Adjust start time (split gap with previous ayah)
            if idx > 0:
                prev_end = self._parse_timestamp(ayah_details[idx - 1]['audio_end_timestamp'])
                gap = start_time - prev_end
                if gap > 0:
                    # Split the gap in the middle
                    adjusted_start = prev_end + (gap // 2)
                else:
                    adjusted_start = start_time
            else:
                # First ayah - use original start time
                adjusted_start = start_time
            
            # Adjust end time (split gap with next ayah)
            if idx < len(ayah_details) - 1:
                next_start = self._parse_timestamp(ayah_details[idx + 1]['audio_start_timestamp'])
                gap = next_start - end_time
                if gap > 0:
                    # Split the gap in the middle
                    adjusted_end = end_time + (gap // 2)
                else:
                    adjusted_end = end_time
            else:
                # Last ayah - use original end time
                adjusted_end = end_time
            
            adjusted_timestamps.append((adjusted_start, adjusted_end))
            
            logger.debug(f"Ayah {idx+1}: Original [{start_time}-{end_time}] → Adjusted [{adjusted_start}-{adjusted_end}]")
        
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
            
            # Calculate adjusted timestamps (split gaps between ayahs)
            adjusted_timestamps = self._calculate_adjusted_timestamps(ayah_details)
            
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
                        # Get adjusted timestamps
                        start_time, end_time = adjusted_timestamps[idx]
                        
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
                        # The gap adjustment means the segment includes some silence
                        relative_actual_start = original_start - start_time
                        relative_actual_end = original_end - start_time
                        
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
                            "silence_gaps": silence_gaps if silence_gaps else []
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
