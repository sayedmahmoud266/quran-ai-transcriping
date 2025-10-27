"""
Chunk Transcription Step - Step 4 of the pipeline.

Transcribes each audio chunk using the Whisper model.
"""

from app.pipeline.base import PipelineStep, PipelineContext
from typing import Dict, Any
from app.inference.transcription import transcription_service
from quran_ayah_lookup import normalize_arabic_text

class ChunkTranscriptionStep(PipelineStep):
    """
    Transcribe each audio chunk using Whisper model.
    
    Input (from context):
        - chunks: List of audio chunks
        - sample_rate: Sample rate
    
    Output (to context):
        - transcriptions: List of transcription results
          Each transcription: {
              'chunk_index': int,
              'text': str,
              'start_time': float,
              'end_time': float,
              'duration': float,
              'word_count': int
          }
    """
    
    def __init__(self, model, processor, device):
        """
        Initialize chunk transcription step.
        
        Args:
            model: Whisper model
            processor: Whisper processor
            device: Device to run model on (cuda/cpu)
        """
        super().__init__()
        self.model = model
        self.processor = processor
        self.device = device
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that chunks are present."""
        if not context.chunks:
            self.logger.error("No chunks in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Transcribe all chunks.
        
        TODO: Implement transcription logic using Whisper model
        
        Args:
            context: Pipeline context with chunks
            
        Returns:
            Context with transcriptions
        """
        import torch
        
        chunks = context.chunks
        sample_rate = context.sample_rate
        audio_array = context.audio_array
        
        self.logger.info(f"Transcribing {len(chunks)} chunks...")
        
        transcriptions = []
        
        for chunk in chunks:

            audio_start = chunk['start_time']
            audio_end = chunk['end_time']

            # Get audio chunk from array
            chunk_audio = audio_array[int(audio_start * sample_rate):int(audio_end * sample_rate)]

            # Transcribe the chunk
            transcription_result = transcription_service.transcribe_bytes(chunk_audio)
            
            # Extract text from result
            text = transcription_result.get('text', '')
            normalized_text = normalize_arabic_text(text)
            word_count = len(normalized_text.split()) if normalized_text else 0

            transcriptions.append({
                'chunk_index': chunk['chunk_index'],
                'text': text,
                'normalized_text': normalized_text,
                'start_time': chunk['start_time'],
                'end_time': chunk['end_time'],
                'duration': chunk['duration'],
                'word_count': word_count
            })
        
        context.transcriptions = transcriptions
        
        self.logger.info(f"Transcribed {len(transcriptions)} chunks")
        
        # Add debug info
        context.add_debug_info(self.name, {
            'total_chunks': len(transcriptions),
            'total_words': sum(t['word_count'] for t in transcriptions),
            'chunks': [{ # with transcription object
                'chunk_index': c['chunk_index'],
                'start_time': c['start_time'],
                'end_time': c['end_time'],
                'duration': c['duration'],
                'transcription_result': transcriptions[c['chunk_index']]
            } for c in chunks]
        })
        
        return context
