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

        Flow:
            1. 
            
        Returns:
            Context with merged chunks
        """
        chunks = context.chunks
        
        self.logger.info(f"Merging {len(chunks)} chunks...")
        
        # TODO: Implement merging logic
        # For now, just pass through
        # merged_chunks = chunks
        merged_chunks = []
        
        # create a list of tuples (duration, List<chunk_index>)
        chunk_durations = [(chunk['duration'], [chunk['chunk_index']]) for chunk in chunks]

        # reduce the list of tuples by adding any consecutive chunks that are less than min_chunk_duration
        merged_chunk_durations = []
        for i in range(len(chunk_durations)):
            if i == 0:
                merged_chunk_durations.append(chunk_durations[i])
            else:
                if chunk_durations[i][0] < self.min_chunk_duration:
                    # Append the chunk index (not the list containing it)
                    merged_chunk_durations[-1][1].append(chunk_durations[i][1][0])
                    # Update the total duration
                    merged_chunk_durations[-1] = (
                        merged_chunk_durations[-1][0] + chunk_durations[i][0],
                        merged_chunk_durations[-1][1]
                    )
                else:
                    merged_chunk_durations.append(chunk_durations[i])

        # convert the list of tuples back to a list of chunks
        merged_chunks = []
        for chunk_duration in merged_chunk_durations:
            merged_chunks.append({
                'duration': chunk_duration[0],
                'chunk_index': chunk_duration[1][0],
                'start_time': chunks[chunk_duration[1][0]]['start_time'],
                'end_time': chunks[chunk_duration[1][-1]]['end_time']
            })

            

        # Re-index chunks
        for idx, chunk in enumerate(merged_chunks):
            chunk['chunk_index'] = idx
        
        context.chunks = merged_chunks
        
        self.logger.info(f"Result: {len(merged_chunks)} chunks after merging")
        
        # Add debug info
        context.add_debug_info(self.name, {
            'original_chunks': len(chunks),
            'merged_chunks': len(merged_chunks),
            'chunks': [{
                'chunk_index': c['chunk_index'],
                'start_time': c['start_time'],
                'end_time': c['end_time'],
                'duration': c['duration']
            } for c in merged_chunks]
        })
        
        return context
