# Enhanced Verse Detection Implementation Plan

## Overview
This document tracks the implementation of the enhanced silence and verse detection algorithm that improves timestamp accuracy through chunk-level transcription and intelligent ayah boundary detection.

---

## Implementation Status

### Phase 1: Silence Detection Enhancement ✅ COMPLETED
**Status**: ✅ Completed (Commit: 34aecaa)

**Objective**: Update silence detection to preserve natural verse boundaries

**Changes Made**:
- ✅ Modified `merge_short_chunks()` in `audio_processor.py`
  - Only merges chunks < 3 seconds
  - Chunks >= 3 seconds are never merged
  - Preserves natural ayah boundaries
- ✅ Updated `transcription_service.py` to use new merging logic
- ✅ Added detailed logging for merge operations

**Files Modified**:
- `app/audio_processor.py`
- `app/transcription_service.py`

---

### Phase 2: Per-Chunk Transcription Tracking
**Status**: ✅ COMPLETED (Commit: TBD)

**Objective**: Track transcribed text for each audio chunk

**Tasks**:
- ✅ Add `transcribed_text` field to chunk dictionary
- ✅ Store chunk-level transcription in chunk results
- ✅ Maintain chunk metadata throughout processing pipeline
- ✅ Update chunk result structure to include:
  ```python
  {
      "chunk_index": int,
      "audio": np.ndarray,
      "start_time": float,
      "end_time": float,
      "transcribed_text": str,  # NEW
      "word_count": int,         # NEW
      "timestamps": List[Dict]
  }
  ```

**Changes Made**:
- ✅ Updated `_transcribe_chunk()` to include `transcribed_text` and `word_count` fields
- ✅ Added `chunk_duration` field for easier calculations
- ✅ Enhanced logging to show chunk details (time range, word count, text preview)
- ✅ Added chunk summary logging after all chunks processed
- ✅ Maintained backward compatibility with existing code

**Files Modified**:
- `app/transcription_service.py`

**Actual Output**:
```python
chunks = [
    {
        "chunk_index": 0,
        "transcribed_text": "بسم الله الرحمن الرحيم",
        "start_time": 0.0,
        "end_time": 2.5
    },
    {
        "chunk_index": 1,
        "transcribed_text": "الم",
        "start_time": 2.5,
        "end_time": 3.2
    },
    # ...
]
```

---

### Phase 3: Duplicate Word Removal
**Status**: ⏳ Pending

**Objective**: Remove duplicate words at boundaries between consecutive chunks

**Algorithm**:
1. For each pair of consecutive chunks (chunk_n, chunk_n+1):
2. Extract words from end of chunk_n
3. Extract words from start of chunk_n+1
4. Find longest common suffix/prefix overlap
5. Remove duplicates from one chunk (prefer removing from start of chunk_n+1)
6. Update word counts and timestamps accordingly

**Example**:
```python
# Before:
chunk_300 = "وَكَذَٰلِكَ يَجۡتَبِيكَ رَبُّكَ وَيُعَلِّمُكَ مِن تَأۡوِيلِ ٱلۡأَحَادِيثِ وَيُتِمُّ نِعۡمَتَهُۥ عَلَيۡكَ وَعَلَىٰٓ ءَالِ يَعۡقُوبَ"
chunk_301 = "وَيُتِمُّ نِعۡمَتَهُۥ عَلَيۡكَ وَعَلَىٰٓ ءَالِ يَعۡقُوبَ كَمَآ أَتَمَّهَا عَلَىٰٓ أَبَوَيۡكَ"

# After:
chunk_300 = "وَكَذَٰلِكَ يَجۡتَبِيكَ رَبُّكَ وَيُعَلِّمُكَ مِن تَأۡوِيلِ ٱلۡأَحَادِيثِ وَيُتِمُّ نِعۡمَتَهُۥ عَلَيۡكَ وَعَلَىٰٓ ءَالِ يَعۡقُوبَ"
chunk_301 = "كَمَآ أَتَمَّهَا عَلَىٰٓ أَبَوَيۡكَ"  # Duplicates removed
```

**Implementation Steps**:
- [ ] Create `_find_word_overlap()` method
- [ ] Create `_remove_duplicate_words()` method
- [ ] Integrate into chunk processing pipeline
- [ ] Update combined transcription logic
- [ ] Adjust timestamps after duplicate removal

**Files to Modify**:
- `app/transcription_service.py` - New methods for duplicate detection
- `app/transcription_service.py` - Update `transcribe_audio()` method

---

### Phase 4: Verse Matching with Chunk Tracking
**Status**: ⏳ Pending

**Objective**: Link detected ayahs to their source chunks (many-to-many relationship)

**Data Structure**:
```python
ayah_chunk_mapping = {
    "55:1": {  # Surah 55, Ayah 1
        "chunks": [0, 1],  # Found in chunks 0 and 1
        "text": "الرَّحْمَٰنُ",
        "word_count": 1
    },
    "55:2": {  # Surah 55, Ayah 2
        "chunks": [1, 2, 3],  # Spans multiple chunks
        "text": "عَلَّمَ الْقُرْآنَ",
        "word_count": 2
    }
}

chunk_ayah_mapping = {
    0: ["55:1"],           # Chunk 0 contains only ayah 1
    1: ["55:1", "55:2"],   # Chunk 1 contains parts of ayahs 1 and 2
    2: ["55:2", "55:3"],   # Chunk 2 contains parts of ayahs 2 and 3
}
```

**Implementation Steps**:
- [ ] Modify `match_verses()` to accept chunk information
- [ ] Create `_map_ayahs_to_chunks()` method
- [ ] Track which chunks contain which ayahs
- [ ] Track which ayahs span which chunks
- [ ] Store mapping for timestamp calculation

**Files to Modify**:
- `app/quran_data.py` - Update `match_verses()` method
- `app/transcription_service.py` - Pass chunk data to verse matching

---

### Phase 5: Advanced Timestamp Detection
**Status**: ⏳ Pending

**Objective**: Calculate accurate ayah timestamps based on chunk-ayah relationships

**Scenarios**:

#### Scenario 1: Ayah Completely in One Chunk (No Other Ayahs)
```python
# Chunk 5 contains ONLY ayah 55:10
# Use chunk boundaries directly
ayah_start = chunk[5].start_time
ayah_end = chunk[5].end_time
```

#### Scenario 2: Ayah Spans Multiple Chunks (No Other Ayahs)
```python
# Ayah 55:15 spans chunks 10, 11, 12 completely
# Use first chunk start and last chunk end
ayah_start = chunk[10].start_time
ayah_end = chunk[12].end_time
```

#### Scenario 3: Ayah in One Chunk with Other Ayahs
```python
# Chunk 20 contains ayahs 55:20, 55:21, 55:22
# Split chunk time proportionally by word count
chunk_duration = chunk[20].end_time - chunk[20].start_time
total_words = chunk[20].word_count

ayah_20_words = 5
ayah_20_duration = (ayah_20_words / total_words) * chunk_duration
ayah_20_start = chunk[20].start_time
ayah_20_end = ayah_20_start + ayah_20_duration
```

#### Scenario 4: Ayah Spans Multiple Chunks with Other Ayahs
```python
# Ayah 55:25 spans chunks 25, 26, 27 with other ayahs mixed in
# Calculate based on word positions across chunks
# Use first occurrence of first word and last occurrence of last word
```

**Implementation Steps**:
- [ ] Create `_calculate_ayah_timestamps()` method
- [ ] Implement scenario 1 detection and calculation
- [ ] Implement scenario 2 detection and calculation
- [ ] Implement scenario 3 detection and calculation
- [ ] Implement scenario 4 detection and calculation
- [ ] Add fallback for edge cases

**Files to Modify**:
- `app/transcription_service.py` - New timestamp calculation method
- `app/transcription_service.py` - Update `_create_verse_details()` method

---

### Phase 6: Silence Splitting Logic Update
**Status**: ⏳ Pending

**Objective**: Split silences between consecutive ayahs only at chunk boundaries

**Rules**:
1. If ayah boundary aligns with chunk boundary:
   - Split silence in half between consecutive ayahs
   - Use existing silence splitting logic
2. If ayah boundary is within a chunk:
   - Do NOT split silence
   - Use word-based time calculation within chunk

**Implementation Steps**:
- [ ] Detect if ayah boundaries align with chunk boundaries
- [ ] Apply silence splitting only for aligned boundaries
- [ ] Skip silence splitting for mid-chunk boundaries
- [ ] Update `_split_silence_between_ayahs()` method

**Files to Modify**:
- `app/transcription_service.py` - Update silence splitting logic

---

## Testing Plan

### Unit Tests
- [ ] Test chunk merging with various durations
- [ ] Test duplicate word detection algorithm
- [ ] Test ayah-to-chunk mapping
- [ ] Test timestamp calculation for each scenario

### Integration Tests
- [ ] Test with single-ayah audio
- [ ] Test with multi-ayah audio (consecutive)
- [ ] Test with long surahs (Surah 2, 55)
- [ ] Test with short surahs (Surah 97, 112)
- [ ] Test with repeated phrases (Surah 55)

### Edge Cases
- [ ] Very short chunks (< 1 second)
- [ ] Very long chunks (> 30 seconds)
- [ ] Chunks with multiple ayahs
- [ ] Ayahs spanning many chunks
- [ ] Overlapping transcriptions
- [ ] Silent periods between ayahs

---

## Performance Considerations

### Memory Usage
- Storing per-chunk transcriptions: ~100 bytes per chunk
- Ayah-chunk mappings: ~50 bytes per ayah
- Expected overhead: < 10 MB for typical audio

### Processing Time
- Duplicate word removal: O(n*m) where n=chunks, m=avg words per chunk
- Ayah-chunk mapping: O(a*c) where a=ayahs, c=chunks
- Timestamp calculation: O(a) where a=ayahs
- Expected overhead: < 500ms for typical audio

---

## Documentation Updates

### Files to Update After Completion
- [ ] `docs/ALGORITHM.md` - Add enhanced detection section
- [ ] `docs/verse_matching.md` - Update with chunk-based matching
- [ ] `docs/AUDIO_SPLITTING.md` - Update with new logic
- [ ] `README.md` - Update features list
- [ ] API documentation - Update response format

---

## Rollback Plan

If issues arise:
1. Revert to commit before Phase 1: `git revert 34aecaa`
2. Old logic preserved in git history
3. Feature flag can be added to toggle new/old algorithm

---

## Success Criteria

✅ **Phase 1**: Chunks >= 3 seconds are never merged
✅ **Phase 2**: Each chunk has transcribed_text field
⏳ **Phase 3**: No duplicate words between consecutive chunks
⏳ **Phase 4**: Accurate ayah-to-chunk mapping
⏳ **Phase 5**: Timestamp accuracy improved by > 50%
⏳ **Phase 6**: Silence splitting only at chunk boundaries

**Overall Goal**: Achieve > 95% timestamp accuracy for ayah boundaries

---

**Last Updated**: 2025-10-04 16:22
**Current Phase**: Phase 3 - Duplicate Word Removal
**Next Action**: Implement duplicate word detection algorithm
