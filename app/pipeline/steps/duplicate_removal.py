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
        - cleaned_transcriptions: Deduplicated transcriptions
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
        
        Checks if the start of each transcription overlaps with the end of the previous one,
        and removes duplicate text from the current transcription.
        """
        transcriptions = context.transcriptions
        
        self.logger.info(f"Removing duplicates from {len(transcriptions)} transcriptions...")
        
        cleaned_transcriptions = []
        duplicates_removed = 0
        
        for i, transcription in enumerate(transcriptions):
            # Create a copy of the transcription to modify
            cleaned_trans = transcription.copy()
            
            # Skip first transcription as there's no previous one to compare
            if i == 0:
                cleaned_transcriptions.append(cleaned_trans)
                continue
            
            # Get current and previous normalized texts
            current_normalized = transcription.get('normalized_text', '')
            previous_normalized = transcriptions[i - 1].get('normalized_text', '')
            
            if not current_normalized or not previous_normalized:
                cleaned_transcriptions.append(cleaned_trans)
                continue
            
            # Split into words for comparison
            current_words = current_normalized.split()
            previous_words = previous_normalized.split()
            
            if not current_words or not previous_words:
                cleaned_transcriptions.append(cleaned_trans)
                continue
            
            # Find overlapping words at the boundary
            # Check how many words from the end of previous match the start of current
            max_overlap = min(len(current_words), len(previous_words))
            overlap_length = 0
            
            for overlap in range(1, max_overlap + 1):
                # Check if last 'overlap' words of previous match first 'overlap' words of current
                if previous_words[-overlap:] == current_words[:overlap]:
                    overlap_length = overlap
            
            # Remove duplicate words from current transcription
            if overlap_length > 0:
                duplicates_removed += 1
                remaining_words = current_words[overlap_length:]
                
                # Update normalized text
                cleaned_trans['normalized_text'] = ' '.join(remaining_words)
                
                # Also update the original text proportionally
                # This is a simple approach - remove the same number of words from original text
                original_text = transcription.get('text', '')
                original_words = original_text.split()
                if len(original_words) >= overlap_length:
                    cleaned_trans['text'] = ' '.join(original_words[overlap_length:])
                
                # Update word count
                cleaned_trans['word_count'] = len(remaining_words)
                
                self.logger.debug(
                    f"Chunk {i}: Removed {overlap_length} duplicate words. "
                    f"Original: {len(current_words)} words, Cleaned: {len(remaining_words)} words"
                )
            
            cleaned_transcriptions.append(cleaned_trans)
        
        # Check if the last chunk's normalized text is "صدق الله العظيم" and remove it
        if cleaned_transcriptions:
            last_chunk_normalized = cleaned_transcriptions[-1].get('normalized_text', '').strip()
            if last_chunk_normalized == 'صدق الله العظيم':
                self.logger.info("Removing last chunk: 'صدق الله العظيم'")
                cleaned_transcriptions.pop()
        
        context.cleaned_transcriptions = cleaned_transcriptions
        
        self.logger.info(
            f"Duplicate removal complete. Processed {len(transcriptions)} transcriptions, "
            f"found duplicates in {duplicates_removed} chunks"
        )
        
        context.add_debug_info(self.name, {
            'transcriptions_processed': len(transcriptions),
            'duplicates_found': duplicates_removed,
            'cleaned_transcriptions_count': len(cleaned_transcriptions),
            'cleaned_transcriptions': cleaned_transcriptions
        })
        
        return context
