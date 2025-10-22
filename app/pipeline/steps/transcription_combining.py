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
        """Validate that cleaned transcriptions are present."""
        if not hasattr(context, 'cleaned_transcriptions') or not context.cleaned_transcriptions:
            self.logger.error("No cleaned_transcriptions in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Combine cleaned transcriptions into final text.
        
        Uses cleaned_transcriptions from duplicate removal step and combines
        the normalized text into a single string.
        """
        cleaned_transcriptions = context.cleaned_transcriptions
        
        self.logger.info(f"Combining {len(cleaned_transcriptions)} cleaned transcriptions...")
        
        # Combine all normalized text from cleaned transcriptions
        combined_transcription_normalized = " ".join([
            t.get('normalized_text', '') 
            for t in cleaned_transcriptions 
            if t.get('normalized_text')
        ])
        
        # Also combine original text for reference
        combined = " ".join([
            t.get('text', '') 
            for t in cleaned_transcriptions 
            if t.get('text')
        ])
        
        context.combined_transcription_normalized = combined_transcription_normalized
        context.final_transcription = combined
        
        self.logger.info(
            f"Combined transcription: {len(combined)} characters, "
            f"normalized: {len(combined_transcription_normalized)} characters"
        )
        
        context.add_debug_info(self.name, {
            'total_transcriptions': len(cleaned_transcriptions),
            'combined_length': len(combined),
            'combined_normalized_length': len(combined_transcription_normalized),
            'word_count': len(combined_transcription_normalized.split()),
            'combined_transcription_normalized': combined_transcription_normalized,
            'combined': combined
        })
        return context
