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
            
            # Merge very short chunks
            chunks = audio_processor.merge_short_chunks(
                chunks,
                min_chunk_duration=1.0,   # Minimum 1 second per chunk
                max_chunk_duration=30.0   # Maximum 30 seconds per chunk
            )
            
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
            
            return {
                "success": True,
                "data": {
                    "exact_transcription": combined_transcription,
                    "details": details
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
        for matched in matched_verses:
            surah = matched['surah']
            ayah = matched['ayah']
            verse_text = matched['text']
            
            # Get timing info
            start_time = matched.get('audio_start_time', 0.0)
            end_time = matched.get('audio_end_time', 0.0)
            
            # If no timing from matching, use overall timestamps
            if start_time == 0.0 and end_time == 0.0 and timestamps:
                start_time = timestamps[0]["start"]
                end_time = timestamps[-1]["end"]
            
            # Count words in the verse
            word_count = quran_data.count_words(verse_text)
            
            detail = {
                "surah_number": surah,
                "ayah_number": ayah,
                "ayah_text_tashkeel": verse_text,
                "ayah_word_count": word_count,
                "start_from_word": 1,
                "end_to_word": word_count,
                "audio_start_timestamp": quran_data._format_timestamp(start_time),
                "audio_end_timestamp": quran_data._format_timestamp(end_time),
                "match_confidence": matched.get('similarity', 0.0)
            }
            details.append(detail)
            
            logger.info(f"Matched: Surah {surah}, Ayah {ayah} (confidence: {matched.get('similarity', 0.0):.2f})")
        
        return details


# Singleton instance
transcription_service = TranscriptionService()
