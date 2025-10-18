"""
Duplicate Removal Step - Step 5 of the pipeline.

Removes duplicate words at chunk boundaries.
"""

from app.pipeline.base import PipelineStep, PipelineContext


class DuplicateRemovalStep(PipelineStep):
    """
    Remove duplicate words at chunk boundaries.
    
    Input (from context):
        - transcriptions: List of transcriptions
    
    Output (to context):
        - transcriptions: Deduplicated transcriptions
    """
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate that transcriptions are present."""
        if not context.transcriptions:
            self.logger.error("No transcriptions in context")
            return False
        return True
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Remove duplicate words between consecutive chunks.
        
        TODO: Implement duplicate removal logic
        """
        transcriptions = context.transcriptions
        
        self.logger.info(f"Removing duplicates from {len(transcriptions)} transcriptions...")
        
        # TODO: Implement duplicate removal
        
        context.add_debug_info(self.name, {
            'transcriptions_processed': len(transcriptions)
        })
        
        return context
