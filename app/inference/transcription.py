"""
Transcription service using the tarteel-ai/whisper-base-ar-quran model.

This module provides model initialization and management.
The actual transcription is handled by the pipeline module.
"""

import torch
import numpy as np
from difflib import SequenceMatcher
from transformers import WhisperProcessor, WhisperForConditionalGeneration, GenerationConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TranscriptionService:
    """
    Service for transcribing Quran recitations using the Whisper model.
    """
    
    MODEL_NAME = "tarteel-ai/whisper-base-ar-quran"
    BASE_MODEL_NAME = "openai/whisper-base"
    
    # Whisper's hard limit is 30 seconds
    # Use 29.5 seconds to be safe and allow for overlap
    MAX_AUDIO_LENGTH_SECONDS = 29.5
    SAMPLE_RATE = 16000
    
    # Silence detection parameters for sub-chunking (progressive fallback)
    # Try multiple settings before resorting to final approach
    SILENCE_ATTEMPTS = [
        {'min_silence_len': 300, 'silence_thresh': -35},  # Attempt 1: moderate
        {'min_silence_len': 250, 'silence_thresh': -30},  # Attempt 2: more aggressive
        {'min_silence_len': 200, 'silence_thresh': -30},  # Attempt 3: very aggressive
    ]
    
    # Final approach when all silence detection attempts fail
    # Options: 'speedup' or 'sliding_window'
    FINAL_APPROACH = 'sliding_window'
    
    # Sliding window parameters
    MIN_OVERLAP_SECONDS = 10  # Minimum overlap between chunks in sliding window approach
    SIMILARITY_THRESHOLD = 0.80  # Threshold for detecting overlapping text
    
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
            generation_config = GenerationConfig.from_pretrained(self.BASE_MODEL_NAME)
            self.model.generation_config = generation_config
            self.model.to(self.device)
            
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
    
    def get_model_info(self):
        """
        Get information about the loaded model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.MODEL_NAME,
            "device": self.device,
            "model_loaded": self.model is not None,
            "processor_loaded": self.processor is not None
        }

    def _transcribe_single_chunk(self, audio_array):
        """
        Transcribe a single audio chunk (must be <= 30 seconds).
        
        Args:
            audio_array: Numpy array or list of audio samples (float32, 16kHz)
        
        Returns:
            Transcription result dictionary with 'text' key
        """
        # Use processor to convert audio to input features (mel spectrograms)
        # The processor expects audio at 16kHz sample rate
        input_features = self.processor(
            audio_array, 
            sampling_rate=self.SAMPLE_RATE, 
            return_tensors="pt"
        ).input_features
        
        # Move to device
        input_features = input_features.to(self.device)
        
        # Generate transcription with timestamps
        predicted_ids = self.model.generate(
            input_features,
            return_timestamps=True
        )
        
        # Decode the transcription
        transcription = self.processor.batch_decode(
            predicted_ids, 
            skip_special_tokens=True
        )

        logger.info(f"Single Chunk Transcription: {transcription[0]}")
        
        return {
            'text': transcription[0],
            'predicted_ids': predicted_ids
        }
    
    def _split_on_silence(self, audio_array: np.ndarray) -> tuple:
        """
        Split long audio into sub-chunks at silence points with progressive fallback.
        Tries multiple silence detection settings before resorting to speed adjustment.
        
        Args:
            audio_array: Audio array to split
            
        Returns:
            Tuple of (sub_chunks: list, was_sped_up: bool, speed_factor: float)
        """
        from pydub import AudioSegment
        from pydub.silence import detect_nonsilent
        
        audio_length_seconds = len(audio_array) / self.SAMPLE_RATE
        max_samples = int(self.MAX_AUDIO_LENGTH_SECONDS * self.SAMPLE_RATE)
        
        # Convert numpy array to pydub AudioSegment
        audio_int16 = (audio_array * 32767).astype(np.int16)
        audio_segment = AudioSegment(
            audio_int16.tobytes(),
            frame_rate=self.SAMPLE_RATE,
            sample_width=audio_int16.dtype.itemsize,
            channels=1
        )
        
        # Try multiple silence detection settings
        for attempt_num, params in enumerate(self.SILENCE_ATTEMPTS, 1):
            min_silence_len = params['min_silence_len']
            silence_thresh = params['silence_thresh']
            
            logger.info(
                f"Silence detection attempt {attempt_num}/{len(self.SILENCE_ATTEMPTS)}: "
                f"min_silence={min_silence_len}ms, thresh={silence_thresh}dB"
            )
            
            # Detect non-silent ranges
            nonsilent_ranges = detect_nonsilent(
                audio_segment,
                min_silence_len=min_silence_len,
                silence_thresh=silence_thresh,
                seek_step=10
            )
            
            if not nonsilent_ranges:
                logger.warning(f"Attempt {attempt_num}: No silence detected")
                continue
            
            # Try to build sub-chunks from detected ranges
            sub_chunks = self._build_chunks_from_ranges(
                audio_array, nonsilent_ranges, max_samples
            )
            
            # Check if all chunks are within the limit
            all_valid = all(len(chunk) <= max_samples for chunk in sub_chunks)
            
            if all_valid and len(sub_chunks) > 1:
                logger.info(
                    f"Attempt {attempt_num}: Successfully split into {len(sub_chunks)} chunks"
                )
                return sub_chunks, False, 1.0
            else:
                logger.warning(
                    f"Attempt {attempt_num}: Failed to create valid chunks "
                    f"(got {len(sub_chunks)} chunks, all_valid={all_valid})"
                )
        
        # All silence detection attempts failed - use final approach
        if self.FINAL_APPROACH == 'speedup':
            logger.warning(
                "All silence detection attempts failed. "
                f"Applying speed adjustment to fit {audio_length_seconds:.2f}s into {self.MAX_AUDIO_LENGTH_SECONDS}s"
            )
            
            speed_factor = audio_length_seconds / self.MAX_AUDIO_LENGTH_SECONDS
            sped_up_audio = self._speed_up_audio(audio_array, speed_factor)
            
            return [sped_up_audio], True, speed_factor
        
        elif self.FINAL_APPROACH == 'sliding_window':
            logger.warning(
                "All silence detection attempts failed. "
                f"Using sliding window approach with {self.MIN_OVERLAP_SECONDS}s overlap"
            )
            
            sub_chunks = self._sliding_window_split(audio_array)
            
            return sub_chunks, False, 1.0
        
        else:
            raise ValueError(f"Unknown FINAL_APPROACH: {self.FINAL_APPROACH}")
    
    def _build_chunks_from_ranges(self, audio_array: np.ndarray, 
                                   nonsilent_ranges: list, 
                                   max_samples: int) -> list:
        """
        Build sub-chunks from non-silent ranges, respecting max length.
        
        Args:
            audio_array: Audio array
            nonsilent_ranges: List of (start_ms, end_ms) tuples
            max_samples: Maximum samples per chunk
            
        Returns:
            List of audio sub-chunks
        """
        sub_chunks = []
        current_chunk_start = 0
        
        for start_ms, end_ms in nonsilent_ranges:
            start_sample = int(start_ms * self.SAMPLE_RATE / 1000)
            end_sample = int(end_ms * self.SAMPLE_RATE / 1000)
            
            # If there's a gap and current accumulated audio would exceed limit
            if current_chunk_start < start_sample:
                accumulated_length = start_sample - current_chunk_start
                if accumulated_length >= max_samples:
                    # Save current chunk up to the silence
                    sub_chunks.append(audio_array[current_chunk_start:start_sample])
                    current_chunk_start = start_sample
            
            # Check if this segment itself is too long
            segment_length = end_sample - start_sample
            if segment_length > max_samples:
                # Save any accumulated audio first
                if start_sample > current_chunk_start:
                    sub_chunks.append(audio_array[current_chunk_start:start_sample])
                
                # This segment is too long even by itself - can't split it
                # Return it as-is and let caller decide
                sub_chunks.append(audio_array[start_sample:end_sample])
                current_chunk_start = end_sample
        
        # Add remaining audio
        if current_chunk_start < len(audio_array):
            remaining = audio_array[current_chunk_start:]
            if len(remaining) > 0:
                sub_chunks.append(remaining)
        
        return sub_chunks if sub_chunks else [audio_array]
    
    def _speed_up_audio(self, audio_array: np.ndarray, speed_factor: float) -> np.ndarray:
        """
        Speed up audio by the given factor using resampling.
        
        Args:
            audio_array: Audio array to speed up
            speed_factor: Speed multiplication factor (e.g., 1.33 for 33% faster)
            
        Returns:
            Sped-up audio array
        """
        from scipy import signal
        
        # Calculate new length
        new_length = int(len(audio_array) / speed_factor)
        
        # Resample to speed up
        sped_up = signal.resample(audio_array, new_length)
        
        logger.info(
            f"Applied {speed_factor:.2f}x speedup: "
            f"{len(audio_array)/self.SAMPLE_RATE:.2f}s -> {new_length/self.SAMPLE_RATE:.2f}s"
        )
        
        return sped_up
    
    def _sliding_window_split(self, audio_array: np.ndarray) -> list:
        """
        Split audio using sliding window with overlap.
        Creates overlapping chunks to avoid hallucinations at boundaries.
        
        Args:
            audio_array: Audio array to split
            
        Returns:
            List of audio sub-chunks with overlap
        """
        max_samples = int(self.MAX_AUDIO_LENGTH_SECONDS * self.SAMPLE_RATE)
        min_overlap_samples = int(self.MIN_OVERLAP_SECONDS * self.SAMPLE_RATE)
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(audio_array):
            end_idx = min(start_idx + max_samples, len(audio_array))
            chunk = audio_array[start_idx:end_idx]
            chunks.append(chunk)
            
            # Calculate remaining audio
            remaining_samples = len(audio_array) - end_idx
            
            if remaining_samples <= 0:
                # No more audio
                break
            elif remaining_samples <= min_overlap_samples:
                # Remaining audio is small, create one more full-sized overlapping chunk
                # Start from position that gives us MIN_OVERLAP with previous chunk
                start_idx = len(audio_array) - max_samples
                if start_idx < 0:
                    start_idx = 0
            else:
                # Move forward by (max_samples - min_overlap_samples) to create overlap
                start_idx = end_idx - min_overlap_samples
        
        logger.info(
            f"Created {len(chunks)} overlapping chunks with ~{self.MIN_OVERLAP_SECONDS}s overlap"
        )
        
        return chunks
    
    def _remove_overlap_with_sequencematcher(self, text1: str, text2: str) -> str:
        """
        Find the best matching sequence between two transcriptions and use it as split point.
        Truncates hallucinations from end of text1 and start of text2.
        
        Args:
            text1: First transcription (end may have hallucinations)
            text2: Second transcription (start may have hallucinations)
            
        Returns:
            Combined text with hallucinations removed
        """
        # Normalize and split into words
        words1 = text1.strip().split()
        words2 = text2.strip().split()
        
        if not words1 or not words2:
            return text1 + ' ' + text2
        
        # Find the best matching sequence anywhere in both texts
        # Use SequenceMatcher to find matching blocks
        str1 = ' '.join(words1)
        str2 = ' '.join(words2)
        matcher = SequenceMatcher(None, str1, str2)
        
        # Get all matching blocks
        matching_blocks = matcher.get_matching_blocks()
        
        # Find the longest/best matching block (excluding the final dummy block)
        best_match = None
        best_match_length = 0
        
        for match in matching_blocks[:-1]:  # Exclude final dummy block
            match_length = match.size
            if match_length > best_match_length and match_length > 20:  # At least 20 characters
                best_match = match
                best_match_length = match_length
        
        if best_match and best_match_length > 20:
            # Found a good match
            # match: (pos_in_str1, pos_in_str2, length)
            pos1_start = best_match.a
            pos1_end = best_match.a + best_match.size
            pos2_start = best_match.b
            pos2_end = best_match.b + best_match.size
            
            # Extract the matching text
            matching_text = str1[pos1_start:pos1_end]
            
            # Split text1 at the end of the match (keep everything up to and including match)
            text1_keep = str1[:pos1_end].strip()
            
            # Split text2 at the end of the match (keep everything after match)
            text2_keep = str2[pos2_end:].strip()
            
            # Combine
            if text2_keep:
                combined = text1_keep + ' ' + text2_keep
            else:
                combined = text1_keep
            
            # Calculate word-level statistics for logging
            match_word_count = len(matching_text.split())
            
            logger.info(
                f"Found matching sequence (~{match_word_count} words, {best_match_length} chars): "
                f"'{matching_text[:50]}...'. "
                f"Truncated hallucinations from both chunks."
            )
            
            return combined
        else:
            # No good match found - try fallback: look for overlap at boundaries
            logger.warning("No strong matching sequence found. Trying boundary overlap detection...")
            
            # Check for overlap at end of text1 and start of text2
            max_check_length = min(len(words1), len(words2), 30)
            best_overlap_length = 0
            best_similarity = 0.0
            
            for overlap_len in range(max_check_length, 2, -1):
                end_words1 = words1[-overlap_len:]
                start_words2 = words2[:overlap_len]
                
                str_end1 = ' '.join(end_words1)
                str_start2 = ' '.join(start_words2)
                
                overlap_matcher = SequenceMatcher(None, str_end1, str_start2)
                similarity = overlap_matcher.ratio()
                
                if similarity >= self.SIMILARITY_THRESHOLD and similarity > best_similarity:
                    best_overlap_length = overlap_len
                    best_similarity = similarity
                    break
            
            if best_overlap_length > 0:
                # Found boundary overlap
                remaining_words = words2[best_overlap_length:]
                result = text1 + ' ' + ' '.join(remaining_words)
                
                logger.info(
                    f"Found {best_overlap_length}-word boundary overlap "
                    f"with {best_similarity:.2%} similarity."
                )
                
                return result
            else:
                # No overlap found at all - just concatenate
                logger.warning("No overlap found. Concatenating chunks as-is.")
                return text1 + ' ' + text2
    
    def _hard_split(self, audio_array: np.ndarray) -> list:
        """
        Fallback: Split audio into fixed-length chunks.
        Used when silence detection fails.
        
        Args:
            audio_array: Audio array to split
            
        Returns:
            List of audio sub-chunks
        """
        max_samples = int(self.MAX_AUDIO_LENGTH_SECONDS * self.SAMPLE_RATE)
        num_chunks = int(np.ceil(len(audio_array) / max_samples))
        
        chunks = []
        for i in range(num_chunks):
            start_idx = i * max_samples
            end_idx = min((i + 1) * max_samples, len(audio_array))
            chunks.append(audio_array[start_idx:end_idx])
        
        return chunks
    
    def transcribe_bytes(self, audio_array):
        """
        Transcribe audio array using the Whisper model.
        Automatically handles audio longer than 30 seconds by splitting into sub-chunks.
        
        Args:
            audio_array: Numpy array or list of audio samples (float32, 16kHz)
        
        Returns:
            Transcription result dictionary with 'text' key
        """
        try:
            # Convert to numpy array if needed
            if not isinstance(audio_array, np.ndarray):
                audio_array = np.array(audio_array)
            
            audio_length_seconds = len(audio_array) / self.SAMPLE_RATE
            logger.info(f"Transcribing audio ({audio_length_seconds:.2f} seconds)...")
            
            # If audio is within the limit, transcribe directly
            if audio_length_seconds <= self.MAX_AUDIO_LENGTH_SECONDS:
                result = self._transcribe_single_chunk(audio_array)
                logger.info(f"Transcription completed: {result['text']}")
                return result
            
            # Audio is too long - split into sub-chunks at silence points
            logger.warning(
                f"Audio length ({audio_length_seconds:.2f}s) exceeds Whisper's limit "
                f"({self.MAX_AUDIO_LENGTH_SECONDS}s). Attempting progressive splitting..."
            )
            
            sub_chunks, was_sped_up, speed_factor = self._split_on_silence(audio_array)
            
            if was_sped_up:
                logger.warning(
                    f"Applied {speed_factor:.2f}x speedup to fit audio within limit. "
                    "Transcription may have slightly altered timing."
                )
            else:
                logger.info(f"Split into {len(sub_chunks)} sub-chunks (approach: {self.FINAL_APPROACH})")
            
            transcriptions = []
            all_predicted_ids = []
            
            for i, sub_chunk in enumerate(sub_chunks):
                sub_length = len(sub_chunk) / self.SAMPLE_RATE
                logger.info(f"Transcribing sub-chunk {i+1}/{len(sub_chunks)} ({sub_length:.2f}s)...")
                
                result = self._transcribe_single_chunk(sub_chunk)
                transcriptions.append(result['text'])
                all_predicted_ids.append(result['predicted_ids'])
            
            # Combine transcriptions
            if self.FINAL_APPROACH == 'sliding_window' and len(transcriptions) > 1:
                # Use SequenceMatcher to find best match and remove overlaps/hallucinations
                combined_text = transcriptions[0]
                for i in range(1, len(transcriptions)):
                    # This method now returns the fully combined text
                    combined_text = self._remove_overlap_with_sequencematcher(
                        combined_text, transcriptions[i]
                    )
                
                logger.info(f"Combined {len(transcriptions)} overlapping chunks with hallucination removal")
            else:
                # Simple concatenation with space
                combined_text = ' '.join(transcriptions)
                logger.info(f"Combined transcription from {len(sub_chunks)} sub-chunks: {combined_text}")
            
            return {
                'text': combined_text,
                'predicted_ids': all_predicted_ids,
                'was_split': True,
                'num_subchunks': len(sub_chunks),
                'was_sped_up': was_sped_up,
                'speed_factor': speed_factor if was_sped_up else 1.0
            }
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise



# Singleton instance
transcription_service = TranscriptionService()
