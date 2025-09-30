# Quran Verse Matching Documentation

## Overview

The Quran AI Transcription API includes intelligent verse matching that identifies the exact surah (chapter) and ayah (verse) numbers from transcribed audio. This feature uses fuzzy text matching combined with audio chunk boundaries to accurately map transcriptions to Quran verses.

## How It Works

### 1. Quran Data Loading

On first startup, the application:
- Downloads complete Quran text from [quran-json repository](https://github.com/risan/quran-json)
- Caches the data locally in `quran_simple.txt`
- Loads 6,236 verses with Arabic text and metadata
- Creates normalized versions (without diacritics) for matching

**Fallback**: If download fails, uses Surah Al-Fatiha (Chapter 1) as fallback data.

### 2. Text Normalization

Both transcribed audio and Quran verses are normalized for matching:

```python
# Removes:
- Diacritics (tashkeel): َ ُ ِ ً ٌ ٍ ّ ْ
- Kashida (tatweel): ـ
- Extra whitespace

# Example:
"بِسْمِ اللَّهِ" → "بسم الله"
```

This ensures matching works even if transcription lacks proper diacritics.

### 3. Matching Algorithms

#### A. Chunk-Based Matching (Primary)

When audio is split into chunks by silence detection:

1. **Split transcription** by chunk boundaries
2. **Match each chunk** to verses independently
3. **Use chunk timing** for verse timestamps
4. **Return multiple verses** if multiple chunks match

**Benefits**:
- Natural verse boundaries align with silence
- More accurate for multi-verse recitations
- Better timestamp accuracy

#### B. Sliding Window Matching (Fallback)

For single-chunk or short audio:

1. **Search entire Quran** for best match
2. **Use Levenshtein distance** for similarity scoring
3. **Return single best match** above threshold

### 4. Similarity Scoring

Uses Levenshtein ratio (0.0 to 1.0):

```python
similarity = levenshtein_ratio(transcription, verse_text)

# Boost score for substring matches
if transcription in verse_text:
    similarity = max(similarity, 0.8)
```

**Minimum threshold**: 0.6 (60% similarity required)

### 5. Confidence Scores

Each matched verse includes a `match_confidence` field:

- **0.9 - 1.0**: Excellent match (near perfect)
- **0.8 - 0.9**: Good match (minor differences)
- **0.7 - 0.8**: Fair match (some discrepancies)
- **0.6 - 0.7**: Acceptable match (significant differences)
- **< 0.6**: No match (returns surah=0, ayah=0)

## API Response Format

### Successful Match

```json
{
  "success": true,
  "data": {
    "exact_transcription": "بسم الله الرحمن الرحيم",
    "details": [
      {
        "surah_number": 1,
        "ayah_number": 1,
        "ayah_text_tashkeel": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "ayah_word_count": 4,
        "start_from_word": 1,
        "end_to_word": 4,
        "audio_start_timestamp": "00:00:00.000",
        "audio_end_timestamp": "00:00:02.500",
        "match_confidence": 0.95
      }
    ]
  }
}
```

### Multiple Verses

```json
{
  "success": true,
  "data": {
    "exact_transcription": "بسم الله الرحمن الرحيم الحمد لله رب العالمين",
    "details": [
      {
        "surah_number": 1,
        "ayah_number": 1,
        "ayah_text_tashkeel": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "ayah_word_count": 4,
        "start_from_word": 1,
        "end_to_word": 4,
        "audio_start_timestamp": "00:00:00.000",
        "audio_end_timestamp": "00:00:02.500",
        "match_confidence": 0.95
      },
      {
        "surah_number": 1,
        "ayah_number": 2,
        "ayah_text_tashkeel": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "ayah_word_count": 4,
        "start_from_word": 1,
        "end_to_word": 4,
        "audio_start_timestamp": "00:00:02.500",
        "audio_end_timestamp": "00:00:05.000",
        "match_confidence": 0.92
      }
    ]
  }
}
```

### No Match Found

```json
{
  "success": true,
  "data": {
    "exact_transcription": "unclear audio",
    "details": [
      {
        "surah_number": 0,
        "ayah_number": 0,
        "ayah_text_tashkeel": "unclear audio",
        "ayah_word_count": 2,
        "start_from_word": 1,
        "end_to_word": 2,
        "audio_start_timestamp": "00:00:00.000",
        "audio_end_timestamp": "00:00:01.000",
        "match_confidence": 0.0
      }
    ]
  }
}
```

**Note**: `surah_number: 0` and `ayah_number: 0` indicate no match was found.

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `surah_number` | integer | Chapter number (1-114, or 0 if no match) |
| `ayah_number` | integer | Verse number within chapter (or 0 if no match) |
| `ayah_text_tashkeel` | string | Complete verse text with diacritics |
| `ayah_word_count` | integer | Number of words in the verse |
| `start_from_word` | integer | Starting word index (always 1 for full verse) |
| `end_to_word` | integer | Ending word index (equals word_count for full verse) |
| `audio_start_timestamp` | string | Start time in format "HH:MM:SS.mmm" |
| `audio_end_timestamp` | string | End time in format "HH:MM:SS.mmm" |
| `match_confidence` | float | Similarity score (0.0 to 1.0) |

## Matching Accuracy

### Factors Affecting Accuracy

**Positive Factors**:
- Clear audio quality
- Proper Tajweed pronunciation
- Natural pauses between verses
- Standard recitation style
- Minimal background noise

**Negative Factors**:
- Poor audio quality
- Non-standard pronunciation
- Continuous recitation without pauses
- Background noise or music
- Incomplete verses

### Expected Performance

| Audio Quality | Expected Confidence | Accuracy |
|---------------|-------------------|----------|
| Excellent | 0.90 - 1.00 | 95-100% correct |
| Good | 0.80 - 0.90 | 85-95% correct |
| Fair | 0.70 - 0.80 | 70-85% correct |
| Poor | 0.60 - 0.70 | 60-70% correct |
| Very Poor | < 0.60 | May not match |

## Configuration

### Adjusting Match Threshold

In `app/quran_data.py`, modify the minimum similarity threshold:

```python
def _find_best_verse_match(self, text: str, min_similarity: float = 0.6):
    # Lower threshold = more lenient matching
    # Higher threshold = stricter matching
```

**Recommended values**:
- **0.5**: Very lenient (may produce false positives)
- **0.6**: Default (balanced)
- **0.7**: Strict (fewer matches, higher accuracy)
- **0.8**: Very strict (only near-perfect matches)

### Chunk Boundary Hints

The matching algorithm uses audio chunk boundaries as hints:

```python
# In transcription_service.py
chunk_info = [
    {"start_time": chunk["start_time"], "end_time": chunk["end_time"]}
    for chunk in chunks
]
matched_verses = quran_data.match_verses(transcription, chunk_info)
```

This helps identify verse boundaries even when transcription is continuous.

## Troubleshooting

### Low Confidence Scores

**Problem**: All matches have confidence < 0.7

**Solutions**:
1. Check audio quality - reduce background noise
2. Ensure proper Arabic pronunciation
3. Verify transcription model is working correctly
4. Lower the `min_similarity` threshold

### Wrong Verses Matched

**Problem**: Incorrect surah/ayah identified

**Solutions**:
1. Increase `min_similarity` threshold
2. Check if audio contains non-Quranic content
3. Verify Quran data loaded correctly
4. Review transcription accuracy first

### No Matches Found (surah=0)

**Problem**: Returns surah_number: 0 for all audio

**Solutions**:
1. Check if Quran data loaded successfully (see logs)
2. Verify transcription is in Arabic
3. Ensure audio contains Quran recitation
4. Lower the `min_similarity` threshold temporarily

### Quran Data Not Loading

**Problem**: "Using fallback Quran data (limited)" in logs

**Solutions**:
1. Check internet connection
2. Verify GitHub is accessible
3. Manually download quran.json and place in project root
4. Check file permissions for writing cache

## Advanced Usage

### Manual Verse Lookup

```python
from app.quran_data import quran_data

# Get specific verse
verse_text = quran_data.get_verse_with_tashkeel(1, 1)
print(verse_text)  # "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ"

# Match custom text
matches = quran_data.match_verses("بسم الله الرحمن الرحيم")
for match in matches:
    print(f"Surah {match['surah']}, Ayah {match['ayah']}")
```

### Custom Matching Logic

Extend `QuranData` class for custom matching:

```python
class CustomQuranData(QuranData):
    def _find_best_verse_match(self, text, min_similarity=0.6):
        # Add custom matching logic
        # e.g., weight certain words higher
        # or use different similarity algorithms
        pass
```

## Performance Considerations

### Memory Usage
- **Quran data**: ~5MB in memory
- **Normalized cache**: ~3MB
- **Total overhead**: ~10MB

### Processing Time
- **First load**: 2-5 seconds (download + parse)
- **Cached load**: < 1 second
- **Per-verse matching**: < 100ms
- **Full transcription**: 200-500ms

### Optimization Tips
1. Keep `quran_simple.txt` cached for faster startup
2. Use chunk-based matching for better accuracy
3. Adjust similarity threshold based on use case
4. Consider parallel matching for very long audio

## Future Enhancements

### Planned Features
1. **Multi-verse detection**: Better handling of continuous recitation
2. **Partial verse matching**: Identify incomplete verses
3. **Recitation style detection**: Adapt matching to different styles
4. **Word-level alignment**: Map each word to verse position
5. **Alternative readings**: Support for different Qira'at

### Possible Improvements
- Use phonetic matching for pronunciation variations
- Implement n-gram matching for better partial matches
- Add support for Tafsir (verse explanations)
- Include verse context (before/after verses)
- Support for verse ranges (e.g., 2:1-5)

## References

- **Quran Data Source**: [quran-json](https://github.com/risan/quran-json)
- **Levenshtein Distance**: [python-Levenshtein](https://pypi.org/project/python-Levenshtein/)
- **Arabic Text Processing**: [PyArabic](https://pypi.org/project/pyarabic/)

## Support

For issues with verse matching:
1. Check the logs for matching confidence scores
2. Verify Quran data loaded successfully
3. Test with known verses (e.g., Al-Fatiha)
4. Report issues with audio samples and expected verses
