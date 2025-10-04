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
            
            # Log chunk summary (before duplicate removal)
            logger.info(f"=== Chunk Summary (Before Duplicate Removal) ===")
            logger.info(f"Total chunks: {len(chunk_results)}")
            total_words_before = sum(r.get("word_count", 0) for r in chunk_results)
            logger.info(f"Total words across all chunks: {total_words_before}")
            for r in chunk_results:
                logger.info(f"  Chunk {r['chunk_index']}: {r['word_count']} words, "
                           f"{r['chunk_duration']:.2f}s, text: {r['transcribed_text'][:50]}...")
            
            # Remove duplicate words between consecutive chunks
            chunk_results = self._remove_duplicate_words(chunk_results)
            
            # Log summary after duplicate removal
            logger.info(f"=== After Duplicate Removal ===")
            total_words_after = sum(r.get("word_count", 0) for r in chunk_results)
            logger.info(f"Total words: {total_words_after} (removed {total_words_before - total_words_after} duplicates)")
            
            # Combine all chunk results (using updated transcribed_text)
            combined_transcription = " ".join([r["transcribed_text"] for r in chunk_results if r["transcribed_text"]])
            combined_timestamps = self._combine_timestamps(chunk_results)
            
            logger.info(f"Combined transcription: {combined_transcription}")
            
            # Match verses using chunk boundaries as hints
            chunk_info = [{"start_time": r["chunk_start_time"], "end_time": r.get("chunk_end_time", 0)} 
                         for r in chunk_results]
            details = self._create_verse_details(combined_transcription, combined_timestamps, chunk_info)
            
            # Create ayah-to-chunk mapping (many-to-many relationship)
            # This will be used for accurate timestamp calculation
            matched_verses = quran_data.match_verses(combined_transcription, chunk_info)
            ayah_chunk_mapping, chunk_ayah_mapping = self._map_ayahs_to_chunks(matched_verses, chunk_results)
            
            # Calculate accurate timestamps using chunk mappings (Phase 5)
            logger.info("=== Calculating Accurate Timestamps ===")
            for detail in details:
                ayah_key = f"{detail['surah_number']}:{detail['ayah_number']}"
                
                if ayah_key in ayah_chunk_mapping:
                    # Store mapping for reference
                    detail['chunk_mapping'] = ayah_chunk_mapping[ayah_key]
                    
                    # Calculate accurate timestamps based on chunk relationships
                    ayah_text = detail.get('ayah_text_tashkeel', '')
                    start_time, end_time = self._calculate_ayah_timestamps(
                        ayah_key,
                        ayah_text,
                        ayah_chunk_mapping,
                        chunk_ayah_mapping,
                        chunk_results
                    )
                    
                    # Update timestamps in detail
                    if start_time > 0 or end_time > 0:
                        detail['audio_start_timestamp'] = quran_data._format_timestamp(start_time)
                        detail['audio_end_timestamp'] = quran_data._format_timestamp(end_time)
                        logger.info(f"Ayah {ayah_key}: Updated timestamps to {detail['audio_start_timestamp']} - {detail['audio_end_timestamp']}")
            
            # Apply chunk-boundary-aware silence splitting (Phase 6)
            details = self._apply_silence_splitting(details, chunk_results)
            
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
            
            # Log chunk information with word count
            words = transcription.split()
            logger.info(f"Chunk {chunk_index} ({chunk_start_time:.2f}s - {chunk_start_time + len(chunk_audio)/sample_rate:.2f}s): "
                       f"{len(words)} words - {transcription[:100]}{'...' if len(transcription) > 100 else ''}")
            
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
                "original_text": transcription,     # FULL original text - preserved for timestamp calculations
                "transcribed_text": transcription,  # Deduplicated text - used for verse matching
                "original_word_count": len(words),  # Original word count (never changes)
                "word_count": len(words),           # Current word count (updated after deduplication)
                "timestamps": timestamps,
                "chunk_index": chunk_index,
                "chunk_start_time": chunk_start_time,
                "chunk_end_time": chunk_start_time + chunk_duration,
                "chunk_duration": chunk_duration
            }
            
        except Exception as e:
            logger.error(f"Error transcribing chunk {chunk_index}: {e}")
            return None
    
    def _find_word_overlap(self, text1: str, text2: str) -> int:
        """
        Find the longest overlap between the end of text1 and the start of text2.
        
        Args:
            text1: First text (earlier chunk)
            text2: Second text (later chunk)
            
        Returns:
            Number of overlapping words
        """
        words1 = text1.split()
        words2 = text2.split()
        
        if not words1 or not words2:
            return 0
        
        max_overlap = 0
        
        # Try different overlap lengths, starting from the longest possible
        max_possible_overlap = min(len(words1), len(words2))
        
        for overlap_len in range(max_possible_overlap, 0, -1):
            # Get last N words from text1
            end_words = words1[-overlap_len:]
            # Get first N words from text2
            start_words = words2[:overlap_len]
            
            # Check if they match
            if end_words == start_words:
                max_overlap = overlap_len
                break
        
        return max_overlap
    
    def _remove_duplicate_words(self, chunk_results: List[Dict]) -> List[Dict]:
        """
        Remove duplicate words at boundaries between consecutive chunks.
        
        IMPORTANT: Only modifies transcribed_text (used for verse matching).
        Preserves original_text (used for timestamp calculations and chunk identification).
        
        Args:
            chunk_results: List of chunk transcription results
            
        Returns:
            Updated list of chunk results with duplicates removed from transcribed_text
        """
        if len(chunk_results) <= 1:
            return chunk_results
        
        logger.info("=== Removing Duplicate Words Between Chunks ===")
        logger.info("NOTE: Only removing from searchable text (transcribed_text)")
        logger.info("      Original text (original_text) preserved for timestamp calculations")
        
        updated_results = []
        
        for i in range(len(chunk_results)):
            current_chunk = chunk_results[i].copy()
            
            if i > 0:
                # Check for overlap with previous chunk
                prev_chunk = updated_results[-1]
                overlap = self._find_word_overlap(
                    prev_chunk["transcribed_text"],
                    current_chunk["transcribed_text"]
                )
                
                if overlap > 0:
                    # Remove overlapping words from transcribed_text ONLY
                    # original_text remains unchanged!
                    words = current_chunk["transcribed_text"].split()
                    remaining_words = words[overlap:]
                    
                    logger.info(f"Chunk {i}: Found {overlap} duplicate words with previous chunk")
                    logger.info(f"  Removed from searchable text: {' '.join(words[:overlap])}")
                    logger.info(f"  Searchable text now: {' '.join(remaining_words) if remaining_words else '[empty]'}")
                    logger.info(f"  Original text preserved: {current_chunk['original_text'][:50]}...")
                    
                    # Update transcribed_text (searchable version)
                    current_chunk["transcribed_text"] = ' '.join(remaining_words)
                    current_chunk["word_count"] = len(remaining_words)
                    
                    # NOTE: original_text and original_word_count remain unchanged
                    # NOTE: timestamps remain unchanged (based on original_text)
                    
                    # Keep transcription field for backward compatibility
                    current_chunk["transcription"] = current_chunk["transcribed_text"]
            
            updated_results.append(current_chunk)
        
        # Log summary
        total_duplicates = sum(
            chunk_results[i]["word_count"] - updated_results[i]["word_count"]
            for i in range(len(chunk_results))
        )
        logger.info(f"Total duplicate words removed from searchable text: {total_duplicates}")
        logger.info(f"Original text corpus preserved for all {len(updated_results)} chunks")
        
        return updated_results
    
    def _map_ayahs_to_chunks(self, matched_verses: List[Dict], chunk_results: List[Dict]) -> tuple:
        """
        Create many-to-many mapping between ayahs and chunks.
        
        This determines which chunks contain which ayahs and vice versa by:
        1. Finding each ayah's text in the chunk transcriptions
        2. Tracking which chunks contain parts of each ayah
        
        Args:
            matched_verses: List of matched ayah dictionaries from verse matching
            chunk_results: List of chunk transcription results
            
        Returns:
            Tuple of (ayah_chunk_mapping, chunk_ayah_mapping)
            - ayah_chunk_mapping: {ayah_key: {"chunks": [indices], "text": str, ...}}
            - chunk_ayah_mapping: {chunk_index: [ayah_keys]}
        """
        from app.quran_data import quran_data
        
        ayah_chunk_mapping = {}
        chunk_ayah_mapping = {i: [] for i in range(len(chunk_results))}
        
        logger.info("=== Mapping Ayahs to Chunks ===")
        
        for verse in matched_verses:
            surah = verse['surah']
            ayah = verse['ayah']
            ayah_key = f"{surah}:{ayah}"
            
            # Get normalized ayah text for matching
            ayah_text = verse.get('text', '')
            ayah_normalized = quran_data.normalize_arabic_text(ayah_text)
            ayah_words = ayah_normalized.split()
            
            if not ayah_words:
                continue
            
            # Find which chunks contain this ayah
            chunks_containing_ayah = []
            
            for chunk_idx, chunk in enumerate(chunk_results):
                # Use original_text for accurate word position tracking
                chunk_normalized = quran_data.normalize_arabic_text(chunk['original_text'])
                
                # Check if ayah text appears in this chunk
                if ayah_normalized in chunk_normalized:
                    chunks_containing_ayah.append(chunk_idx)
                else:
                    # Check for partial match (at least 50% of ayah words)
                    chunk_words = chunk_normalized.split()
                    matching_words = sum(1 for word in ayah_words if word in chunk_words)
                    
                    if matching_words >= len(ayah_words) * 0.5:
                        chunks_containing_ayah.append(chunk_idx)
            
            # Store mapping
            if chunks_containing_ayah:
                ayah_chunk_mapping[ayah_key] = {
                    "surah": surah,
                    "ayah": ayah,
                    "chunks": chunks_containing_ayah,
                    "text": ayah_text,
                    "word_count": len(ayah_words)
                }
                
                # Update reverse mapping
                for chunk_idx in chunks_containing_ayah:
                    if ayah_key not in chunk_ayah_mapping[chunk_idx]:
                        chunk_ayah_mapping[chunk_idx].append(ayah_key)
                
                logger.info(f"Ayah {ayah_key}: Found in chunks {chunks_containing_ayah}")
            else:
                logger.warning(f"Ayah {ayah_key}: Not found in any chunk!")
        
        # Log summary
        logger.info(f"=== Mapping Summary ===")
        logger.info(f"Total ayahs mapped: {len(ayah_chunk_mapping)}")
        logger.info(f"Chunk-to-Ayah mapping:")
        for chunk_idx, ayah_keys in chunk_ayah_mapping.items():
            if ayah_keys:
                logger.info(f"  Chunk {chunk_idx}: {len(ayah_keys)} ayahs - {', '.join(ayah_keys)}")
        
        return ayah_chunk_mapping, chunk_ayah_mapping
    
    def _calculate_ayah_timestamps(
        self, 
        ayah_key: str,
        ayah_text: str,
        ayah_chunk_mapping: Dict,
        chunk_ayah_mapping: Dict,
        chunk_results: List[Dict]
    ) -> tuple:
        """
        Calculate accurate timestamps for an ayah based on its chunk relationships.
        
        Implements 4 scenarios:
        1. Ayah completely in one chunk (no other ayahs) - use chunk boundaries
        2. Ayah spans multiple chunks (no other ayahs) - use first/last chunk boundaries
        3. Ayah in one chunk (with other ayahs) - proportional time split by word count
        4. Ayah spans multiple chunks (with other ayahs) - word position-based calculation
        
        Args:
            ayah_key: Ayah identifier (e.g., "55:1")
            ayah_text: Full ayah text
            ayah_chunk_mapping: Mapping of ayahs to chunks
            chunk_ayah_mapping: Mapping of chunks to ayahs
            chunk_results: List of chunk transcription results
            
        Returns:
            Tuple of (start_time, end_time) in seconds
        """
        from app.quran_data import quran_data
        
        if ayah_key not in ayah_chunk_mapping:
            logger.warning(f"Ayah {ayah_key} not found in chunk mapping, using fallback")
            return (0.0, 0.0)
        
        ayah_info = ayah_chunk_mapping[ayah_key]
        chunk_indices = ayah_info['chunks']
        
        if not chunk_indices:
            return (0.0, 0.0)
        
        # Normalize ayah text for matching
        ayah_normalized = quran_data.normalize_arabic_text(ayah_text)
        ayah_words = ayah_normalized.split()
        
        # SCENARIO 1: Ayah completely in ONE chunk with NO other ayahs
        if len(chunk_indices) == 1:
            chunk_idx = chunk_indices[0]
            chunk = chunk_results[chunk_idx]
            ayahs_in_chunk = chunk_ayah_mapping.get(chunk_idx, [])
            
            if len(ayahs_in_chunk) == 1:
                # Perfect! Use chunk boundaries directly
                logger.info(f"Ayah {ayah_key}: Scenario 1 - Single chunk, no other ayahs")
                return (chunk['chunk_start_time'], chunk['chunk_end_time'])
            
            # SCENARIO 3: Ayah in ONE chunk WITH other ayahs
            else:
                logger.info(f"Ayah {ayah_key}: Scenario 3 - Single chunk with {len(ayahs_in_chunk)} ayahs")
                return self._calculate_proportional_time(
                    ayah_key, ayah_words, chunk, ayahs_in_chunk, 
                    ayah_chunk_mapping, chunk_results
                )
        
        # SCENARIO 2 or 4: Ayah spans MULTIPLE chunks
        else:
            # Check if ayah is the ONLY ayah in all its chunks
            has_other_ayahs = False
            for chunk_idx in chunk_indices:
                ayahs_in_chunk = chunk_ayah_mapping.get(chunk_idx, [])
                if len(ayahs_in_chunk) > 1:
                    has_other_ayahs = True
                    break
            
            if not has_other_ayahs:
                # SCENARIO 2: Ayah spans multiple chunks, NO other ayahs
                logger.info(f"Ayah {ayah_key}: Scenario 2 - Spans {len(chunk_indices)} chunks, no other ayahs")
                first_chunk = chunk_results[chunk_indices[0]]
                last_chunk = chunk_results[chunk_indices[-1]]
                return (first_chunk['chunk_start_time'], last_chunk['chunk_end_time'])
            
            # SCENARIO 4: Ayah spans multiple chunks WITH other ayahs
            else:
                logger.info(f"Ayah {ayah_key}: Scenario 4 - Spans {len(chunk_indices)} chunks with other ayahs")
                return self._calculate_word_position_time(
                    ayah_key, ayah_words, chunk_indices, chunk_results
                )
    
    def _calculate_proportional_time(
        self,
        ayah_key: str,
        ayah_words: List[str],
        chunk: Dict,
        ayahs_in_chunk: List[str],
        ayah_chunk_mapping: Dict,
        chunk_results: List[Dict]
    ) -> tuple:
        """
        Scenario 3: Calculate time proportionally when ayah shares a chunk with other ayahs.
        Split chunk time based on word count ratios.
        """
        chunk_duration = chunk['chunk_duration']
        chunk_start = chunk['chunk_start_time']
        
        # Calculate total words in chunk from all ayahs
        total_words = 0
        ayah_word_counts = {}
        
        for other_ayah_key in ayahs_in_chunk:
            if other_ayah_key in ayah_chunk_mapping:
                word_count = ayah_chunk_mapping[other_ayah_key]['word_count']
                ayah_word_counts[other_ayah_key] = word_count
                total_words += word_count
        
        if total_words == 0:
            return (chunk_start, chunk_start + chunk_duration)
        
        # Calculate this ayah's proportion
        ayah_word_count = len(ayah_words)
        ayah_proportion = ayah_word_count / total_words
        ayah_duration = chunk_duration * ayah_proportion
        
        # Find position of this ayah among ayahs in chunk
        ayah_position = ayahs_in_chunk.index(ayah_key)
        
        # Calculate start time based on previous ayahs
        time_before = 0.0
        for i in range(ayah_position):
            prev_ayah = ayahs_in_chunk[i]
            if prev_ayah in ayah_word_counts:
                prev_proportion = ayah_word_counts[prev_ayah] / total_words
                time_before += chunk_duration * prev_proportion
        
        start_time = chunk_start + time_before
        end_time = start_time + ayah_duration
        
        logger.info(f"  Proportional split: {ayah_word_count}/{total_words} words = {ayah_proportion:.2%} of chunk")
        logger.info(f"  Time: {start_time:.2f}s - {end_time:.2f}s (duration: {ayah_duration:.2f}s)")
        
        return (start_time, end_time)
    
    def _calculate_word_position_time(
        self,
        ayah_key: str,
        ayah_words: List[str],
        chunk_indices: List[int],
        chunk_results: List[Dict]
    ) -> tuple:
        """
        Scenario 4: Calculate time based on word positions across multiple chunks.
        Find first occurrence of first word and last occurrence of last word.
        """
        from app.quran_data import quran_data
        
        if not ayah_words:
            first_chunk = chunk_results[chunk_indices[0]]
            last_chunk = chunk_results[chunk_indices[-1]]
            return (first_chunk['chunk_start_time'], last_chunk['chunk_end_time'])
        
        first_word = ayah_words[0]
        last_word = ayah_words[-1]
        
        start_time = None
        end_time = None
        
        # Find first occurrence of first word
        for chunk_idx in chunk_indices:
            chunk = chunk_results[chunk_idx]
            chunk_normalized = quran_data.normalize_arabic_text(chunk['original_text'])
            chunk_words = chunk_normalized.split()
            
            if first_word in chunk_words:
                # Found first word, calculate its position
                word_position = chunk_words.index(first_word)
                chunk_duration = chunk['chunk_duration']
                time_per_word = chunk_duration / len(chunk_words) if chunk_words else 0
                
                start_time = chunk['chunk_start_time'] + (word_position * time_per_word)
                logger.info(f"  First word '{first_word}' found at position {word_position} in chunk {chunk_idx}")
                break
        
        # Find last occurrence of last word (search backwards)
        for chunk_idx in reversed(chunk_indices):
            chunk = chunk_results[chunk_idx]
            chunk_normalized = quran_data.normalize_arabic_text(chunk['original_text'])
            chunk_words = chunk_normalized.split()
            
            if last_word in chunk_words:
                # Found last word, calculate its position
                # Use last occurrence if word appears multiple times
                word_positions = [i for i, w in enumerate(chunk_words) if w == last_word]
                word_position = word_positions[-1] if word_positions else 0
                
                chunk_duration = chunk['chunk_duration']
                time_per_word = chunk_duration / len(chunk_words) if chunk_words else 0
                
                end_time = chunk['chunk_start_time'] + ((word_position + 1) * time_per_word)
                logger.info(f"  Last word '{last_word}' found at position {word_position} in chunk {chunk_idx}")
                break
        
        # Fallback to chunk boundaries if words not found
        if start_time is None:
            start_time = chunk_results[chunk_indices[0]]['chunk_start_time']
            logger.warning(f"  First word not found, using chunk start")
        
        if end_time is None:
            end_time = chunk_results[chunk_indices[-1]]['chunk_end_time']
            logger.warning(f"  Last word not found, using chunk end")
        
        logger.info(f"  Word-based time: {start_time:.2f}s - {end_time:.2f}s")
        
        return (start_time, end_time)
    
    def _check_boundary_alignment(
        self,
        ayah_timestamp: float,
        chunk_results: List[Dict],
        tolerance_ms: float = 100.0
    ) -> bool:
        """
        Check if an ayah boundary aligns with a chunk boundary.
        
        Args:
            ayah_timestamp: Ayah boundary time in seconds
            chunk_results: List of chunk transcription results
            tolerance_ms: Tolerance in milliseconds for alignment detection
            
        Returns:
            True if ayah boundary aligns with a chunk boundary
        """
        tolerance_sec = tolerance_ms / 1000.0
        
        for chunk in chunk_results:
            chunk_start = chunk['chunk_start_time']
            chunk_end = chunk['chunk_end_time']
            
            # Check if ayah timestamp is close to chunk start or end
            if abs(ayah_timestamp - chunk_start) <= tolerance_sec:
                return True
            if abs(ayah_timestamp - chunk_end) <= tolerance_sec:
                return True
        
        return False
    
    def _apply_silence_splitting(
        self,
        details: List[Dict],
        chunk_results: List[Dict]
    ) -> List[Dict]:
        """
        Apply silence splitting between consecutive ayahs ONLY at chunk boundaries.
        
        Phase 6: If ayah boundary is within a chunk (not at boundary),
        do NOT split silence - use the calculated timestamp as-is.
        
        Args:
            details: List of verse details with timestamps
            chunk_results: List of chunk transcription results
            
        Returns:
            Updated list of verse details with adjusted timestamps
        """
        if len(details) <= 1:
            return details
        
        logger.info("=== Phase 6: Chunk-Boundary-Aware Silence Splitting ===")
        
        updated_details = []
        
        for i, detail in enumerate(details):
            updated_detail = detail.copy()
            
            # Convert timestamps to seconds
            def ts_to_sec(ts_str):
                parts = ts_str.split(':')
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
            
            current_end = ts_to_sec(detail['audio_end_timestamp'])
            
            # Check if there's a next ayah
            if i < len(details) - 1:
                next_start = ts_to_sec(details[i + 1]['audio_start_timestamp'])
                gap = next_start - current_end
                
                # Only split silence if BOTH boundaries align with chunk boundaries
                current_end_aligned = self._check_boundary_alignment(current_end, chunk_results)
                next_start_aligned = self._check_boundary_alignment(next_start, chunk_results)
                
                if current_end_aligned and next_start_aligned and gap > 0:
                    # Both boundaries are at chunk edges - safe to split silence
                    silence_midpoint = current_end + (gap / 2.0)
                    
                    from app.quran_data import quran_data
                    updated_detail['audio_end_timestamp'] = quran_data._format_timestamp(silence_midpoint)
                    
                    logger.info(f"Ayah {detail['surah_number']}:{detail['ayah_number']}: "
                               f"Split silence at chunk boundary (gap: {gap:.2f}s)")
                else:
                    # At least one boundary is mid-chunk - do NOT split
                    if gap > 0:
                        logger.info(f"Ayah {detail['surah_number']}:{detail['ayah_number']}: "
                                   f"Skipping silence split (mid-chunk boundary, gap: {gap:.2f}s)")
            
            updated_details.append(updated_detail)
        
        return updated_details
    
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
