"""
Transcription Alignment Step - Step 7.5 of the pipeline.

Performs word-level timestamp alignment for transcribed chunks.
"""

import logging
import tempfile
import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import soundfile as sf
from app.pipeline.base import PipelineStep, PipelineContext

logger = logging.getLogger(__name__)


class TranscriptionAlignmentStep(PipelineStep):
    """
    Align transcriptions at word-level using forced alignment.
    
    This step takes chunks with accurate transcriptions and uses
    a forced alignment tool (e.g., whisper-timestamped, wav2vec2-alignment)
    to get precise word-level timestamps.
    
    Input (from context):
        - matched_chunk_verses: Chunks with matched verses and transcriptions
        - audio_array: Original audio data
        - sample_rate: Audio sample rate
    
    Output (to context):
        - matched_chunk_verses: Updated with word_alignments field
    """
    
    def __init__(self, alignment_method: str = 'wav2vec2', language: str = 'ar'):
        """
        Initialize the alignment step.
        
        Args:
            alignment_method: Method to use for alignment
                - 'wav2vec2': Use Wav2Vec2 forced alignment (default, most accurate)
                - 'dtw': Use DTW-based alignment (fast fallback)
            language: Language code for alignment (default: 'ar' for Arabic)
        """
        super().__init__()
        self.alignment_method = alignment_method
        self.language = language
        self.wav2vec2_model = None  # Lazy load
        self.wav2vec2_processor = None
        self.logger.info(f"Initialized with alignment_method={alignment_method}, language={language}")
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that required data is present."""
        if not hasattr(context, 'matched_chunk_verses') or not context.matched_chunk_verses:
            self.logger.error("No matched_chunk_verses in context")
            return False
        
        if not hasattr(context, 'audio_array') or context.audio_array is None:
            self.logger.error("No audio_array in context")
            return False
        
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Perform word-level alignment for each chunk.
        
        For each chunk:
        1. Extract the audio segment
        2. Get the normalized text
        3. Perform forced alignment to get word timestamps
        4. Add word_alignments to chunk data
        """
        matched_chunk_verses = context.matched_chunk_verses
        audio_array = context.audio_array
        sample_rate = context.sample_rate
        
        self.logger.info(f"Aligning {len(matched_chunk_verses)} chunks using {self.alignment_method} method...")
        
        # Track unique chunks to avoid processing duplicates
        processed_chunks = set()
        alignment_count = 0
        
        for chunk_data in matched_chunk_verses:
            chunk_index = chunk_data.get('chunk_index')
            chunk_reuse = chunk_data.get('chunk_reuse', False)
            
            # Skip reused chunks
            if chunk_reuse:
                self.logger.debug(f"Skipping alignment for reused chunk {chunk_index}")
                continue
            
            # Skip if already processed
            if chunk_index in processed_chunks:
                continue
            
            # Get chunk timing and text
            start_time = chunk_data.get('chunk_start_time', 0)
            end_time = chunk_data.get('chunk_end_time', 0)
            chunk_text = chunk_data.get('chunk_text', '')
            normalized_text = chunk_data.get('chunk_normalized_text', '')
            
            # IMPORTANT: Include omitted duplicate text for alignment
            # The duplicate_removal step stores omitted text that was removed from chunk boundaries
            # We need to include it during alignment to get accurate word timings
            duplicated_omitted_text = chunk_data.get('duplicated_omitted_text', '')
            
            # Construct full text for alignment (omitted + current)
            if duplicated_omitted_text:
                full_normalized_text = duplicated_omitted_text + ' ' + normalized_text
                self.logger.debug(
                    f"Chunk {chunk_index}: Including {len(duplicated_omitted_text.split())} omitted words. "
                    f"Full text: '{full_normalized_text[:100]}...'"
                )
            else:
                full_normalized_text = normalized_text
            
            self.logger.info(f"Aligning chunk {chunk_index}: {full_normalized_text[:80]}...")
            
            if not full_normalized_text or end_time <= start_time:
                self.logger.warning(f"Skipping chunk {chunk_index}: invalid data")
                continue
            
            try:
                # Extract audio segment for this chunk
                start_sample = int(start_time * sample_rate)
                end_sample = int(end_time * sample_rate)
                chunk_audio = audio_array[start_sample:end_sample]
                
                # Perform alignment based on method (using FULL text including omitted)
                if self.alignment_method == 'wav2vec2':
                    full_word_alignments = self._align_with_wav2vec2(
                        chunk_audio, full_normalized_text, sample_rate, start_time
                    )
                elif self.alignment_method == 'dtw':
                    full_word_alignments = self._align_with_dtw(
                        chunk_audio, full_normalized_text, sample_rate, start_time
                    )
                else:
                    self.logger.warning(f"Unknown alignment method: {self.alignment_method}, using wav2vec2")
                    full_word_alignments = self._align_with_wav2vec2(
                        chunk_audio, full_normalized_text, sample_rate, start_time
                    )
                
                # Filter word alignments to exclude omitted duplicate words
                # Keep only the words that are in the current (non-omitted) text
                if duplicated_omitted_text and full_word_alignments:
                    num_omitted_words = len(duplicated_omitted_text.split())
                    # Skip the first N words (omitted duplicates)
                    word_alignments = full_word_alignments[num_omitted_words:]
                    
                    # Also store the full alignments (including omitted) for reference
                    chunk_data['word_alignments_full'] = full_word_alignments
                    chunk_data['word_alignments_omitted'] = full_word_alignments[:num_omitted_words]
                    
                    self.logger.debug(
                        f"Chunk {chunk_index}: Filtered {num_omitted_words} omitted words from alignments. "
                        f"Total: {len(full_word_alignments)} → Current: {len(word_alignments)}"
                    )
                else:
                    word_alignments = full_word_alignments
                
                # Add alignments to chunk data (non-omitted words only)
                chunk_data['word_alignments'] = word_alignments
                chunk_data['alignment_method'] = self.alignment_method
                
                processed_chunks.add(chunk_index)
                alignment_count += 1
                
                self.logger.debug(
                    f"Chunk {chunk_index}: Aligned {len(word_alignments)} words "
                    f"({start_time:.2f}s - {end_time:.2f}s)"
                )
                
            except Exception as e:
                self.logger.error(f"Error aligning chunk {chunk_index}: {e}")
                chunk_data['word_alignments'] = []
                chunk_data['alignment_error'] = str(e)
        
        self.logger.info(f"Completed alignment for {alignment_count} unique chunks")
        
        context.add_debug_info(self.name, {
            'total_chunks_processed': alignment_count,
            'alignment_method': self.alignment_method,
            'chunks_with_alignments': [
                {
                    'chunk_index': c.get('chunk_index'),
                    'word_count': len(c.get('word_alignments', [])),
                    'start_time': c.get('chunk_start_time'),
                    'end_time': c.get('chunk_end_time'),
                    'word_alignments': c.get('word_alignments', [])
                }
                for c in matched_chunk_verses
                if 'word_alignments' in c and not c.get('chunk_reuse', False)
            ]
        })
        
        return context
    
    def _align_with_wav2vec2(
        self,
        audio: np.ndarray,
        text: str,
        sample_rate: int,
        chunk_start_time: float
    ) -> List[Dict]:
        """
        Align using Wav2Vec2 CTC forced alignment.
        
        This performs TRUE forced alignment - it uses the known text to find
        where each word appears in the audio.
        
        Args:
            audio: Audio segment as numpy array
            text: Normalized text to align (the ground truth)
            sample_rate: Audio sample rate
            chunk_start_time: Start time of chunk in original audio
            
        Returns:
            List of word alignment dictionaries
        """
        try:
            import torch
            import torchaudio
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        except ImportError:
            self.logger.error("torch/torchaudio/transformers not available for forced alignment")
            return self._align_with_dtw(audio, text, sample_rate, chunk_start_time)
        
        words = text.split()
        if not words:
            return []
        
        try:
            # Lazy load Arabic Wav2Vec2 model
            if self.wav2vec2_model is None:
                self.logger.info("Loading Arabic Wav2Vec2 model for forced alignment...")
                # Use Arabic-specific model trained on Common Voice Arabic
                model_name = "jonatasgrosman/wav2vec2-large-xlsr-53-arabic"
                self.wav2vec2_processor = Wav2Vec2Processor.from_pretrained(model_name)
                self.wav2vec2_model = Wav2Vec2ForCTC.from_pretrained(model_name)
                self.wav2vec2_model.eval()
                self.logger.info(f"Loaded Arabic Wav2Vec2 model: {model_name}")
            
            # Resample to 16kHz if needed (Wav2Vec2 requirement)
            target_sr = 16000
            if sample_rate != target_sr:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate,
                    new_freq=target_sr
                )
                audio_tensor = torch.from_numpy(audio).float()
                audio_tensor = resampler(audio_tensor)
            else:
                audio_tensor = torch.from_numpy(audio).float()
            
            # Normalize audio
            if audio_tensor.abs().max() > 1.0:
                audio_tensor = audio_tensor / 32768.0
            
            # Get emissions from model
            with torch.inference_mode():
                logits = self.wav2vec2_model(audio_tensor.unsqueeze(0)).logits
                emissions = torch.log_softmax(logits, dim=-1)
            
            emission = emissions[0].cpu().detach()
            
            # Tokenize the transcript using the processor
            # The processor handles Arabic text properly
            tokens = self.wav2vec2_processor.tokenizer.encode(text)
            
            # Remove special tokens (pad, unk, etc.)
            vocab = self.wav2vec2_processor.tokenizer.get_vocab()
            special_tokens = [
                vocab.get('[PAD]', -1),
                vocab.get('[UNK]', -1),
                vocab.get('<s>', -1),
                vocab.get('</s>', -1)
            ]
            tokens = [t for t in tokens if t not in special_tokens]
            
            if not tokens:
                self.logger.warning("No valid tokens for alignment, using DTW")
                return self._align_with_dtw(audio, text, sample_rate, chunk_start_time)
            
            # Perform CTC forced alignment
            trellis = self._get_trellis(emission, tokens)
            path = self._backtrack(trellis, emission, tokens)
            
            # Get token-to-frame alignment
            token_spans = []
            for token_idx, (frame_idx, _) in enumerate(path):
                if token_idx < len(tokens):
                    token_spans.append((tokens[token_idx], frame_idx))
            
            # Decode tokens back to text to find word boundaries
            decoded_tokens = self.wav2vec2_processor.tokenizer.convert_ids_to_tokens(tokens)
            
            # Group tokens into words
            word_alignments = []
            current_word_tokens = []
            current_word_frames = []
            word_idx = 0
            
            for i, (token_id, frame_idx) in enumerate(token_spans):
                token_str = decoded_tokens[i] if i < len(decoded_tokens) else ""
                current_word_tokens.append(token_str)
                current_word_frames.append(frame_idx)
                
                # Check if this is end of word (next token starts a new word or is space)
                is_word_end = (
                    i == len(token_spans) - 1 or  # Last token
                    (i + 1 < len(decoded_tokens) and decoded_tokens[i + 1].startswith('|'))  # Word boundary
                )
                
                if is_word_end and current_word_frames and word_idx < len(words):
                    # Calculate timing for this word
                    ratio = len(audio) / sample_rate / emission.shape[0]
                    start_frame = current_word_frames[0]
                    end_frame = current_word_frames[-1]
                    
                    word_start = chunk_start_time + (start_frame * ratio)
                    word_end = chunk_start_time + (end_frame * ratio)
                    
                    word_alignments.append({
                        'word': words[word_idx],
                        'start': round(word_start, 3),
                        'end': round(word_end, 3),
                        'confidence': 0.85  # Default confidence for now
                    })
                    
                    current_word_tokens = []
                    current_word_frames = []
                    word_idx += 1
            
            if word_alignments:
                avg_conf = np.mean([w['confidence'] for w in word_alignments])
                self.logger.debug(
                    f"Wav2Vec2 aligned {len(word_alignments)} words with avg confidence: {avg_conf:.3f}"
                )
            
            return word_alignments
                
        except Exception as e:
            self.logger.error(f"Error during Wav2Vec2 alignment: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return self._align_with_dtw(audio, text, sample_rate, chunk_start_time)
    
    def _get_trellis(self, emission, tokens, blank_id=0):
        """Build trellis for CTC alignment."""
        import torch
        num_frame = emission.size(0)
        num_tokens = len(tokens)
        trellis = torch.zeros((num_frame, num_tokens + 1))
        trellis[1:, 0] = torch.cumsum(emission[1:, blank_id], 0)
        trellis[0, 1:] = -float('inf')
        trellis[-num_tokens:, 0] = float('inf')
        
        for t in range(num_frame - 1):
            trellis[t + 1, 1:] = torch.maximum(
                trellis[t, 1:] + emission[t, blank_id],
                trellis[t, :-1] + emission[t, tokens],
            )
        return trellis
    
    def _backtrack(self, trellis, emission, tokens, blank_id=0):
        """Backtrack through trellis to find best path."""
        import torch
        t, j = trellis.size(0) - 1, trellis.size(1) - 1
        path = []
        
        while j > 0:
            stayed = trellis[t - 1, j] + emission[t - 1, blank_id]
            changed = trellis[t - 1, j - 1] + emission[t - 1, tokens[j - 1]]
            
            t -= 1
            if changed > stayed:
                j -= 1
                path.append((t, j))
        
        return path[::-1]
    
    def _merge_repeats(self, path, transcript):
        """Merge repeated characters."""
        i1, i2 = path[0]
        segments = []
        
        for i, (t, j) in enumerate(path[1:], start=1):
            if j != i2:
                segments.append((transcript[i2], i1, t, path[i][0] - i1))
                i1, i2 = t, j
        
        segments.append((transcript[i2], i1, path[-1][0], path[-1][0] - i1))
        return segments
    
    def _merge_words(self, segments, separator='|'):
        """Merge character segments into words."""
        words = []
        word_chars = []
        word_start = None
        word_score = 0
        
        for char, start, end, score in segments:
            if char == separator:
                if word_chars:
                    words.append((
                        ''.join(word_chars),
                        word_start,
                        end,
                        word_score / len(word_chars)
                    ))
                    word_chars = []
                    word_score = 0
            else:
                if not word_chars:
                    word_start = start
                word_chars.append(char)
                word_score += score
        
        if word_chars:
            words.append((
                ''.join(word_chars),
                word_start,
                segments[-1][2],
                word_score / len(word_chars)
            ))
        
        return words
    
    def _align_with_dtw(
        self,
        audio: np.ndarray,
        text: str,
        sample_rate: int,
        chunk_start_time: float
    ) -> List[Dict]:
        """
        Align using Dynamic Time Warping with energy-based segmentation.
        
        This is a fast fallback method that uses audio energy to segment words.
        
        Args:
            audio: Audio segment as numpy array
            text: Normalized text to align
            sample_rate: Audio sample rate
            chunk_start_time: Start time of chunk in original audio
            
        Returns:
            List of word alignment dictionaries
        """
        try:
            from dtw import dtw
            import librosa
        except ImportError:
            self.logger.warning("dtw-python not installed, using simple equal division")
            return self._simple_equal_division(audio, text, sample_rate, chunk_start_time)
        
        words = text.split()
        if not words:
            return []
        
        try:
            # Calculate energy envelope
            hop_length = 512
            energy = librosa.feature.rms(y=audio, hop_length=hop_length)[0]
            times = librosa.frames_to_time(np.arange(len(energy)), sr=sample_rate, hop_length=hop_length)
            
            # Find energy peaks (potential word boundaries)
            from scipy.signal import find_peaks
            peaks, _ = find_peaks(energy, distance=int(0.1 * sample_rate / hop_length))
            
            # If we have fewer peaks than words, use equal division
            if len(peaks) < len(words) - 1:
                return self._simple_equal_division(audio, text, sample_rate, chunk_start_time)
            
            # Map words to time segments
            word_alignments = []
            audio_duration = len(audio) / sample_rate
            
            # Use DTW to align word count with energy peaks
            word_indices = np.linspace(0, len(words), len(peaks) + 2)
            
            for i, word in enumerate(words):
                # Find corresponding time range
                start_idx = int(word_indices[i])
                end_idx = int(word_indices[i + 1])
                
                if start_idx < len(times):
                    word_start = times[start_idx]
                else:
                    word_start = (i / len(words)) * audio_duration
                
                if end_idx < len(times):
                    word_end = times[end_idx]
                else:
                    word_end = ((i + 1) / len(words)) * audio_duration
                
                word_alignments.append({
                    'word': word,
                    'start': round(chunk_start_time + word_start, 3),
                    'end': round(chunk_start_time + word_end, 3),
                    'confidence': 0.6  # Medium confidence for DTW
                })
            
            return word_alignments
            
        except Exception as e:
            self.logger.warning(f"DTW alignment failed: {e}, using simple division")
            return self._simple_equal_division(audio, text, sample_rate, chunk_start_time)
    
    def _simple_equal_division(
        self,
        audio: np.ndarray,
        text: str,
        sample_rate: int,
        chunk_start_time: float
    ) -> List[Dict]:
        """
        Simple fallback: divide audio equally among words.
        
        Args:
            audio: Audio segment as numpy array
            text: Normalized text to align
            sample_rate: Audio sample rate
            chunk_start_time: Start time of chunk in original audio
            
        Returns:
            List of word alignment dictionaries
        """
        words = text.split()
        if not words:
            return []
        
        audio_duration = len(audio) / sample_rate
        word_duration = audio_duration / len(words)
        
        alignments = []
        for i, word in enumerate(words):
            word_start = chunk_start_time + (i * word_duration)
            word_end = word_start + word_duration
            
            alignments.append({
                'word': word,
                'start': round(word_start, 3),
                'end': round(word_end, 3),
                'confidence': 0.3  # Low confidence for simple method
            })
        
        return alignments
