"""
Transcription Combining Step - Step 6 of the pipeline.

Combines all chunk transcriptions into final transcription.
"""

from app.pipeline.base import PipelineStep, PipelineContext


class TranscriptionCombiningStep(PipelineStep):
    """
    Combine all transcriptions into final text.
    
    Input (from context):
        - transcriptions: List of transcriptions
    
    Output (to context):
        - final_transcription: Combined transcription text
    """
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that transcriptions are present."""
        if not context.transcriptions:
            self.logger.error("No transcriptions in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Combine transcriptions.
        
        TODO: Implement combining logic
        """
        transcriptions = context.transcriptions
        
        self.logger.info(f"Combining {len(transcriptions)} transcriptions...")
        
        # TODO: Implement proper combining
        combined = " ".join([t.get('text', '') for t in transcriptions if t.get('text')])
        
        context.final_transcription = combined
        
        self.logger.info(f"Combined transcription: {len(combined)} characters")
        
        context.add_debug_info(self.name, {
            'total_transcriptions': len(transcriptions),
            'combined_length': len(combined)
        })
        
        return context
