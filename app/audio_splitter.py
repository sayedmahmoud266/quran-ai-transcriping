"""
Audio splitting module for extracting individual ayahs from audio files.
"""

import os
import io
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
    
    def split_audio_by_ayahs(
        self,
        audio_file_path: str,
        ayah_details: List[Dict]
    ) -> Tuple[io.BytesIO, str]:
        """
        Split audio file into individual ayah segments and create a zip file.
        
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
                # Try generic loader
                audio = AudioSegment.from_file(audio_file_path)
            
            logger.info(f"Audio loaded: duration={len(audio)/1000:.2f}s, channels={audio.channels}, sample_rate={audio.frame_rate}Hz")
            
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
            
            # Create zip file
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                logger.info(f"Creating zip file with {len(ayah_details)} ayahs")
                
                for idx, detail in enumerate(ayah_details):
                    try:
                        # Get timestamps
                        start_time = self._parse_timestamp(detail['audio_start_timestamp'])
                        end_time = self._parse_timestamp(detail['audio_end_timestamp'])
                        
                        # Extract segment
                        segment = audio[start_time:end_time]
                        
                        # Generate filename
                        surah = detail['surah_number']
                        ayah = detail['ayah_number']
                        is_basmala = detail.get('is_basmala', False)
                        
                        if is_basmala:
                            filename = f"surah_{surah:03d}_basmala{file_ext}"
                        else:
                            filename = f"surah_{surah:03d}_ayah_{ayah:03d}{file_ext}"
                        
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
                        
                        logger.debug(f"Added {filename} to zip (duration: {len(segment)/1000:.2f}s)")
                        
                    except Exception as e:
                        logger.error(f"Error processing ayah {idx+1}: {e}")
                        continue
                
                # Add a README file
                readme_content = f"""Quran Audio Ayah Segments
========================

Surah: {surah_num}
Total Ayahs: {len(ayah_details)}
Format: {file_ext}

Files are named as:
- surah_XXX_basmala{file_ext} (for Basmala)
- surah_XXX_ayah_YYY{file_ext} (for regular ayahs)

Where:
- XXX = Surah number (3 digits)
- YYY = Ayah number (3 digits)

Generated by Quran AI Transcription API v2.0.0
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
