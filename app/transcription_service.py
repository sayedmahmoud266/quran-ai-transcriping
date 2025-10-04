"""
Transcription service using the tarteel-ai/whisper-base-ar-quran model.
"""

import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import numpy as np
from typing import Dict, List, Optional
import logging

from app.audio_processor import audio_processor
from app.quran_data import quran_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Service for transcribing Quran recitations using the Whisper model.
    """
    
    MODEL_NAME = "tarteel-ai/whisper-base-ar-quran"
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the Whisper model and processor."""
        try:
            logger.info(f"Loading model: {self.MODEL_NAME}")
            
            # Determine device (GPU if available, else CPU)
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")
            
            # Load processor and model
            self.processor = WhisperProcessor.from_pretrained(self.MODEL_NAME)
            self.model = WhisperForConditionalGeneration.from_pretrained(self.MODEL_NAME)
            self.model.to(self.device)
            
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def transcribe_audio(self, audio_array: np.ndarray, sample_rate: int) -> Dict:
        """
        Transcribe audio to Quran text with timestamps.
        Splits audio into chunks by silence detection for better accuracy.
        
        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate of the audio
            
        Returns:
            Dictionary with transcription results
        """
        try:
            # Validate audio
            if not audio_processor.validate_audio(audio_array):
                raise ValueError("Invalid audio data")
            
            logger.info("Splitting audio into chunks by silence detection...")
            
            # Split audio by silence
            chunks = audio_processor.split_audio_by_silence(
                audio_array,
                sample_rate,
                min_silence_len=500,  # 500ms of silence
                silence_thresh=-40,    # -40 dBFS threshold
                keep_silence=200       # Keep 200ms of silence at edges
            )
            
            # Merge ONLY very short chunks (< 3 seconds)
            # Longer chunks are preserved to maintain natural verse boundaries
            chunks = audio_processor.merge_short_chunks(chunks)
            
            logger.info(f"Processing {len(chunks)} audio chunks...")
            
            # Process each chunk
            chunk_results = []
            for chunk in chunks:
                chunk_result = self._transcribe_chunk(
                    chunk["audio"],
                    sample_rate,
                    chunk["start_time"],
                    chunk["chunk_index"]
                )
                if chunk_result:
                    chunk_results.append(chunk_result)
            
            # Combine all chunk results
            combined_transcription = " ".join([r["transcription"] for r in chunk_results])
            combined_timestamps = self._combine_timestamps(chunk_results)
            
            logger.info(f"Combined transcription: {combined_transcription}")
            
            # Match verses using chunk boundaries as hints
            chunk_info = [{"start_time": r["chunk_start_time"], "end_time": r.get("chunk_end_time", 0)} 
                         for r in chunk_results]
            details = self._create_verse_details(combined_transcription, combined_timestamps, chunk_info)
            
            # Validate and correct verse boundaries (feedback loop)
            logger.info("Running validation and correction feedback loop...")
            details = self._validate_and_correct_verses(details, combined_transcription, combined_timestamps)
            
            # Calculate diagnostic timestamps
            audio_input_end_timestamp = chunk_results[-1].get("chunk_end_time", 0) if chunk_results else 0
            last_ayah_end_timestamp = details[-1]["audio_end_timestamp"] if details else "00:00:00.000"
            
            # Convert timestamp string to seconds
            def timestamp_to_seconds(ts_str):
                parts = ts_str.split(':')
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            
            # Calculate ayah elapsed times
            total_ayahs_elapsed_time = 0
            total_silences_between_ayahs_time = 0
            
            for i, detail in enumerate(details):
                start_sec = timestamp_to_seconds(detail["audio_start_timestamp"])
                end_sec = timestamp_to_seconds(detail["audio_end_timestamp"])
                ayah_duration = end_sec - start_sec
                total_ayahs_elapsed_time += ayah_duration
                
                # Calculate silence between this ayah and next
                if i < len(details) - 1:
                    next_start_sec = timestamp_to_seconds(details[i + 1]["audio_start_timestamp"])
                    silence = next_start_sec - end_sec
                    total_silences_between_ayahs_time += silence
            
            last_ayah_end_sec = timestamp_to_seconds(last_ayah_end_timestamp) if details else 0
            remaining_trailing_audio_time = audio_input_end_timestamp - last_ayah_end_sec
            
            # Format time helper
            def seconds_to_timestamp(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = seconds % 60
                return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
            
            return {
                "success": True,
                "data": {
                    "exact_transcription": combined_transcription,
                    "details": details,
                    "word_timestamps": combined_timestamps,  # Add word timestamps for audio splitting
                    "diagnostics": {
                        "audio_input_end_timestamp": seconds_to_timestamp(audio_input_end_timestamp),
                        "last_ayah_end_timestamp": last_ayah_end_timestamp,
                        "total_ayahs_elapsed_time": seconds_to_timestamp(total_ayahs_elapsed_time),
                        "total_silences_between_ayahs_time": seconds_to_timestamp(total_silences_between_ayahs_time),
                        "remaining_trailing_audio_time": seconds_to_timestamp(remaining_trailing_audio_time),
                        "time_difference": seconds_to_timestamp(audio_input_end_timestamp - total_ayahs_elapsed_time - total_silences_between_ayahs_time)
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _transcribe_chunk(
        self, 
        chunk_audio: np.ndarray, 
        sample_rate: int,
        chunk_start_time: float,
        chunk_index: int
    ) -> Optional[Dict]:
        """
        Transcribe a single audio chunk.
        
        Args:
            chunk_audio: Audio data for the chunk
            sample_rate: Sample rate
            chunk_start_time: Start time of chunk in original audio
            chunk_index: Index of the chunk
            
        Returns:
            Dictionary with chunk transcription and timestamps
        """
        try:
            # Process audio for the model
            input_features = self.processor(
                chunk_audio,
                sampling_rate=sample_rate,
                return_tensors="pt"
            ).input_features
            
            # Move to device
            input_features = input_features.to(self.device)
            
            # Generate transcription
            with torch.no_grad():
                predicted_ids = self.model.generate(input_features)
            
            # Decode the transcription
            transcription = self.processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True
            )[0]
            
            if not transcription.strip():
                return None
            
            logger.info(f"Chunk {chunk_index}: {transcription}")
            
            # Create timestamps for this chunk
            chunk_duration = len(chunk_audio) / sample_rate
            words = transcription.split()
            
            timestamps = []
            if words:
                time_per_word = chunk_duration / len(words)
                for i, word in enumerate(words):
                    timestamps.append({
                        "word": word,
                        "start": chunk_start_time + (i * time_per_word),
                        "end": chunk_start_time + ((i + 1) * time_per_word)
                    })
            
            return {
                "transcription": transcription,
                "timestamps": timestamps,
                "chunk_index": chunk_index,
                "chunk_start_time": chunk_start_time,
                "chunk_end_time": chunk_start_time + chunk_duration
            }
            
        except Exception as e:
            logger.error(f"Error transcribing chunk {chunk_index}: {e}")
            return None
    
    def _combine_timestamps(self, chunk_results: List[Dict]) -> List[Dict]:
        """
        Combine timestamps from all chunks into a single list.
        
        Args:
            chunk_results: List of chunk transcription results
            
        Returns:
            Combined list of timestamps
        """
        combined_timestamps = []
        for chunk_result in chunk_results:
            combined_timestamps.extend(chunk_result["timestamps"])
        return combined_timestamps
    
    def _extract_timestamps(self, transcription: str, 
                          audio_array: np.ndarray, 
                          sample_rate: int) -> List[Dict]:
        """
        Create approximate word-level timestamps based on audio duration.
        
        Args:
            transcription: Transcribed text
            audio_array: Original audio array
            sample_rate: Sample rate
            
        Returns:
            List of timestamp dictionaries
        """
        # Create approximate timestamps based on audio length
        # In production, you could use a forced alignment tool like wav2vec2
        # or other ASR models that provide word-level timestamps
        
        audio_duration = len(audio_array) / sample_rate
        
        words = transcription.split()
        num_words = len(words)
        
        if num_words == 0:
            return []
        
        # Create approximate timestamps (evenly distributed)
        # This is a simplification - in production, use proper alignment
        timestamps = []
        time_per_word = audio_duration / num_words
        
        for i, word in enumerate(words):
            start_time = i * time_per_word
            end_time = (i + 1) * time_per_word
            timestamps.append({
                "word": word,
                "start": start_time,
                "end": end_time
            })
        
        return timestamps
    
    def _validate_and_correct_verses(
        self,
        details: List[Dict],
        transcription: str,
        timestamps: List[Dict]
    ) -> List[Dict]:
        """
        Validate verse boundaries and correct misalignments.
        This is a feedback loop that checks if each ayah's audio matches its text.
        
        Args:
            details: Initial verse details
            transcription: Full transcription text
            timestamps: Word-level timestamps
            
        Returns:
            Corrected verse details
        """
        if not details or len(details) < 2:
            return details
        
        logger.info(f"Validating {len(details)} ayahs...")
        
        # Normalize transcription for comparison
        transcription_normalized = quran_data.normalize_arabic_text(transcription)
        transcription_words = transcription_normalized.split()
        
        corrected_details = []
        word_index = 0
        
        for idx, detail in enumerate(details):
            # Get expected ayah text
            expected_text = quran_data.normalize_arabic_text(detail['ayah_text_tashkeel'])
            expected_words = expected_text.split()
            expected_word_count = len(expected_words)
            
            # Extract actual words from transcription at current position
            if word_index + expected_word_count <= len(transcription_words):
                actual_words = transcription_words[word_index:word_index + expected_word_count]
                actual_text = ' '.join(actual_words)
                
                # Calculate similarity
                from rapidfuzz import fuzz
                similarity = fuzz.ratio(expected_text, actual_text) / 100.0
                
                logger.debug(f"Ayah {detail['ayah_number']}: Expected {expected_word_count} words, similarity: {similarity:.2f}")
                
                # If similarity is too low, try to find the correct boundary
                # But only if it's significantly low (< 60%) to avoid over-correction
                if similarity < 0.60:
                    logger.warning(f"Low similarity ({similarity:.2f}) for Ayah {detail['ayah_number']}, attempting correction...")
                    
                    # Search for best match in a window
                    best_match_index = word_index
                    best_similarity = similarity
                    search_window = min(20, len(transcription_words) - word_index)
                    
                    for offset in range(-5, search_window):
                        test_start = max(0, word_index + offset)
                        test_end = min(len(transcription_words), test_start + expected_word_count)
                        
                        if test_end - test_start == expected_word_count:
                            test_words = transcription_words[test_start:test_end]
                            test_text = ' '.join(test_words)
                            test_similarity = fuzz.ratio(expected_text, test_text) / 100.0
                            
                            if test_similarity > best_similarity:
                                best_similarity = test_similarity
                                best_match_index = test_start
                    
                    # Only apply correction if improvement is significant (> 10%)
                    if best_similarity > similarity + 0.10:
                        logger.info(f"  → Corrected position: word {word_index} → {best_match_index}, similarity: {similarity:.2f} → {best_similarity:.2f}")
                        word_index = best_match_index
                        similarity = best_similarity
                    else:
                        logger.info(f"  → No significant improvement found, keeping original position")
                elif similarity >= 0.60:
                    logger.debug(f"Ayah {detail['ayah_number']}: Good similarity ({similarity:.2f}), no correction needed")
                
                # Calculate timestamps based on corrected word positions
                if word_index < len(timestamps) and word_index + expected_word_count <= len(timestamps):
                    start_time = timestamps[word_index]["start"]
                    end_time = timestamps[word_index + expected_word_count - 1]["end"]
                    
                    # Update detail with corrected timestamps
                    corrected_detail = detail.copy()
                    corrected_detail["audio_start_timestamp"] = quran_data._format_timestamp(start_time)
                    corrected_detail["audio_end_timestamp"] = quran_data._format_timestamp(end_time)
                    corrected_detail["match_confidence"] = similarity
                    corrected_detail["start_from_word"] = 1
                    corrected_detail["end_to_word"] = expected_word_count
                    
                    corrected_details.append(corrected_detail)
                    
                    # Move to next ayah
                    word_index += expected_word_count
                else:
                    # Keep original if we can't correct
                    logger.warning(f"  → Could not correct Ayah {detail['ayah_number']}, keeping original")
                    corrected_details.append(detail)
                    word_index += expected_word_count
            else:
                # Not enough words left, keep original
                corrected_details.append(detail)
                break
        
        logger.info(f"Validation complete: {len(corrected_details)} ayahs validated")
        return corrected_details
    
    def _create_verse_details(self, transcription: str, 
                            timestamps: List[Dict],
                            chunk_boundaries: List[Dict] = None) -> List[Dict]:
        """
        Create detailed verse information from transcription and timestamps.
        Uses Quran database for accurate verse matching.
        
        Args:
            transcription: Full transcription text
            timestamps: Word-level timestamps
            chunk_boundaries: Audio chunk boundaries as hints for verse detection
            
        Returns:
            List of verse detail dictionaries
        """
        if not timestamps:
            return []
        
        # Use Quran data to match verses
        matched_verses = quran_data.match_verses(transcription, chunk_boundaries)
        
        if not matched_verses:
            logger.warning("No verses matched, returning transcription as-is")
            # Fallback: return transcription without verse matching
            start_time = timestamps[0]["start"] if timestamps else 0.0
            end_time = timestamps[-1]["end"] if timestamps else 0.0
            
            return [{
                "surah_number": 0,
                "ayah_number": 0,
                "ayah_text_tashkeel": transcription,
                "ayah_word_count": len(transcription.split()),
                "start_from_word": 1,
                "end_to_word": len(transcription.split()),
                "audio_start_timestamp": quran_data._format_timestamp(start_time),
                "audio_end_timestamp": quran_data._format_timestamp(end_time),
                "match_confidence": 0.0
            }]
        
        # Create details from matched verses
        details = []
        cumulative_time = 0.0
        
        for idx, matched in enumerate(matched_verses):
            surah = matched['surah']
            ayah = matched['ayah']
            verse_text = matched['text']
            is_basmala = matched.get('is_basmala', False)
            
            # Get timing info
            start_time = matched.get('audio_start_time', 0.0)
            end_time = matched.get('audio_end_time', 0.0)
            
            # If no timing from matching, estimate based on position
            if start_time == 0.0 and end_time == 0.0 and timestamps:
                # Distribute time across verses proportionally
                total_duration = timestamps[-1]["end"] - timestamps[0]["start"]
                verse_duration = total_duration / len(matched_verses)
                start_time = timestamps[0]["start"] + (idx * verse_duration)
                end_time = start_time + verse_duration
            
            # Count words in the verse
            word_count = quran_data.count_words(verse_text)
            
            # Normalize text for searching
            verse_text_normalized = quran_data.normalize_arabic_text(verse_text)
            
            # Calculate offsets in milliseconds
            start_time_ms = int(start_time * 1000)
            end_time_ms = int(end_time * 1000)
            
            detail = {
                "surah_number": surah,
                "ayah_number": ayah,
                "ayah_text_tashkeel": verse_text,
                "ayah_text_normalized": verse_text_normalized,
                "ayah_word_count": word_count,
                "start_from_word": 1,
                "end_to_word": word_count,
                "audio_start_timestamp": quran_data._format_timestamp(start_time),
                "audio_end_timestamp": quran_data._format_timestamp(end_time),
                "audio_start_offset_absolute_ms": start_time_ms,
                "audio_end_offset_absolute_ms": end_time_ms,
                "match_confidence": matched.get('similarity', 0.0)
            }
            
            # Add Basmala indicator if applicable
            if is_basmala:
                detail["is_basmala"] = True
            
            details.append(detail)
            
            ayah_desc = "Basmala" if is_basmala else f"Ayah {ayah}"
            logger.info(f"Matched: Surah {surah}, {ayah_desc} (confidence: {matched.get('similarity', 0.0):.2f})")
        
        return details


# Singleton instance
transcription_service = TranscriptionService()
