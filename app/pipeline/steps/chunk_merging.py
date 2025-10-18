"""
Chunk Merging Step - Step 3 of the pipeline.

Merges short chunks or chunks with small silence gaps.
"""

from app.pipeline.base import PipelineStep, PipelineContext
import numpy as np


class ChunkMergingStep(PipelineStep):
    """
    Merge short chunks or chunks with small silence gaps.
    
    Input (from context):
        - chunks: List of audio chunks
    
    Output (to context):
        - chunks: Merged list of audio chunks
    """
    
    def __init__(self, 
                 min_chunk_duration: float = 3.0,
                 min_silence_gap: float = 0.5):
        """
        Initialize chunk merging step.
        
        Args:
            min_chunk_duration: Minimum chunk duration in seconds (default: 3.0s)
            min_silence_gap: Minimum silence gap to keep chunks separate (default: 0.5s)
        """
        super().__init__()
        self.min_chunk_duration = min_chunk_duration
        self.min_silence_gap = min_silence_gap
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that chunks are present."""
        if not context.chunks:
            self.logger.error("No chunks in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Merge short chunks.
        
        TODO: Implement chunk merging logic
        
        Args:
            context: Pipeline context with chunks
            
        Returns:
            Context with merged chunks
        """
        chunks = context.chunks
        
        self.logger.info(f"Merging {len(chunks)} chunks...")
        
        # TODO: Implement merging logic
        # For now, just pass through
        merged_chunks = chunks
        
        # Re-index chunks
        for idx, chunk in enumerate(merged_chunks):
            chunk['chunk_index'] = idx
        
        context.chunks = merged_chunks
        
        self.logger.info(f"Result: {len(merged_chunks)} chunks after merging")
        
        # Add debug info
        context.add_debug_info(self.name, {
            'original_chunks': len(chunks),
            'merged_chunks': len(merged_chunks)
        })
        
        return context
