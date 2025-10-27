# Quran Data Module Removal

**Date:** 2025-10-18  
**Status:** Complete

## What Was Removed

The `app/quran_data.py` file has been removed from the project as it will be replaced with a separate approach for Quran data management.

## Files Modified

### 1. **`app/queue/worker.py`**
- Removed `from app.quran_data import quran_data` import
- Removed `quran_data` parameter from `create_full_pipeline()` call

### 2. **`app/pipeline/orchestrator.py`**
- Removed `quran_data` parameter from `create_full_pipeline()` signature
- Removed `quran_data` parameter from `create_partial_pipeline()` signature
- Removed `quran_data` parameter from `VerseMatchingStep()` instantiation

### 3. **`app/pipeline/steps/verse_matching.py`**
- Removed `quran_data` parameter from `__init__()`
- Removed `self.quran_data` instance variable
- Added note to implement custom verse matching logic

### 4. **`app/utils/audio_splitter.py`**
- Removed `from app.quran_data import quran_data` import
- Replaced `quran_data.normalize_arabic_text()` with inline normalization function
- Uses basic regex-based Arabic text normalization

## Impact

### VerseMatchingStep
The `VerseMatchingStep` now has a placeholder implementation. You need to implement your own verse matching logic:

```python
class VerseMatchingStep(PipelineStep):
    def __init__(self):
        super().__init__()
        # Add your own initialization here
    
    def process(self, context: PipelineContext) -> PipelineContext:
        # TODO: Implement your verse matching logic
        transcription = context.final_transcription
        
        # Your implementation here
        matched_verses = []
        
        context.matched_verses = matched_verses
        return context
```

### Audio Splitter
The audio splitter now uses inline text normalization instead of relying on `quran_data`:

```python
# Basic Arabic text normalization
import re
ayah_text_normalized = re.sub(r'[\u064B-\u065F\u0670\u0610-\u061A\u06D6-\u06ED]', '', ayah_text)
ayah_text_normalized = ayah_text_normalized.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
ayah_text_normalized = ayah_text_normalized.replace('ة', 'ه')
ayah_text_normalized = ' '.join(ayah_text_normalized.split())
```

## Next Steps

### 1. Implement Verse Matching
You need to implement the verse matching logic in `app/pipeline/steps/verse_matching.py`:

```python
def process(self, context: PipelineContext) -> PipelineContext:
    transcription = context.final_transcription
    
    # Your verse matching implementation
    # Options:
    # - Use external API
    # - Use separate library
    # - Implement custom algorithm
    # - Use database lookup
    
    matched_verses = your_matching_function(transcription)
    
    context.matched_verses = matched_verses
    return context
```

### 2. Provide Verse Data
The pipeline expects `matched_verses` to have this structure:

```python
matched_verses = [
    {
        'surah': 1,
        'ayah': 1,
        'text': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
        'start_time': 0.0,
        'end_time': 2.5,
        # ... other fields
    },
    # ... more verses
]
```

### 3. Update Verse Details Format
The `verse_details` in the context should have this structure for the audio splitter:

```python
verse_details = [
    {
        'surah_number': 1,
        'ayah_number': 1,
        'ayah_text_tashkeel': 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
        'audio_start_timestamp': '00:00:00.000',
        'audio_end_timestamp': '00:00:02.500',
        # ... other fields
    },
    # ... more verses
]
```

## Alternatives for Quran Data

You can implement verse matching using:

1. **External API**
   - Quran.com API
   - Alquran Cloud API
   - Custom API

2. **Separate Library**
   - Create a separate package
   - Import as needed
   - Keep it decoupled

3. **Database**
   - Store Quran text in database
   - Query for matching
   - Cache results

4. **File-based**
   - Load from JSON/CSV files
   - Parse on startup
   - Keep in memory

## Example Implementation

Here's a simple example using an external approach:

```python
# app/pipeline/steps/verse_matching.py

class VerseMatchingStep(PipelineStep):
    def __init__(self):
        super().__init__()
        # Initialize your verse matcher
        self.verse_matcher = YourVerseMatcherClass()
    
    def process(self, context: PipelineContext) -> PipelineContext:
        transcription = context.final_transcription
        chunks = context.chunks
        
        self.logger.info(f"Matching verses for transcription...")
        
        # Use your custom matching logic
        matched_verses = self.verse_matcher.match(
            text=transcription,
            chunks=chunks
        )
        
        context.matched_verses = matched_verses
        
        self.logger.info(f"Matched {len(matched_verses)} verses")
        
        context.add_debug_info(self.name, {
            'total_verses': len(matched_verses)
        })
        
        return context
```

## Summary

✅ **`app/quran_data.py` removed**  
✅ **All references updated**  
✅ **Pipeline still functional**  
✅ **Ready for custom implementation**  

You now have a clean slate to implement verse matching using your preferred approach!
