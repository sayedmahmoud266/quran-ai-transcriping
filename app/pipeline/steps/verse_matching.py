"""
Verse Matching Step - Step 7 of the pipeline.

Matches transcribed text to Quran verses.
"""

from app.pipeline.base import PipelineStep, PipelineContext


class VerseMatchingStep(PipelineStep):
    """
    Match transcription to Quran verses.
    
    Input (from context):
        - final_transcription: Combined transcription
        - chunks: Chunk boundaries (for hints)
    
    Output (to context):
        - matched_verses: List of matched verses
    
    Note: Implement your own verse matching logic here.
    """
    
    def __init__(self):
        """
        Initialize verse matching step.
        """
        super().__init__()
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that transcription is present."""
        if not context.final_transcription:
            self.logger.error("No final transcription in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Match verses.
        
        TODO: Implement verse matching logic
        """
        transcription = context.final_transcription
        
        self.logger.info(f"Matching verses for transcription ({len(transcription)} chars)...")
        
        # TODO: Implement verse matching
        matched_verses = []
        
        context.matched_verses = matched_verses
        
        self.logger.info(f"Matched {len(matched_verses)} verses")
        
        context.add_debug_info(self.name, {
            'total_verses': len(matched_verses)
        })
        
        return context
