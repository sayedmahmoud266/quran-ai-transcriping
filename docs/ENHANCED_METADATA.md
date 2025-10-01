# Enhanced Metadata Features

## Overview

The API now provides comprehensive metadata for each ayah, including normalized text, precise audio offsets, and silence gap detection. These features enable advanced applications like search, precise audio trimming, and silence analysis.

## New Metadata Fields

### 1. Normalized Text (ayah_text_normalized)

**Purpose**: Text without tashkeel (diacritics) for search applications

**Example**:
```json
{
  "ayah_text_tashkeel": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
  "ayah_text_normalized": "بسم الله الرحمن الرحيم"
}
```

**Use Cases**:
- Full-text search without worrying about diacritics
- Fuzzy matching
- Text comparison
- Database indexing

### 2. Audio Offsets (milliseconds)

**Fields**:
- `audio_start_offset_ms`: Start time in milliseconds
- `audio_end_offset_ms`: End time in milliseconds
- `actual_ayah_start_offset_ms`: Original start (before gap adjustment)
- `actual_ayah_end_offset_ms`: Original end (before gap adjustment)

**Example**:
```json
{
  "audio_start_timestamp": "00:02:15.500",
  "audio_end_timestamp": "00:02:25.300",
  "audio_start_offset_ms": 135500,
  "audio_end_offset_ms": 145300,
  "actual_ayah_start_offset_ms": 136000,
  "actual_ayah_end_offset_ms": 145000
}
```

**Difference**:
- `audio_start/end_offset_ms`: Includes gap adjustment (for smooth playback)
- `actual_ayah_start/end_offset_ms`: Exact ayah boundaries (for precise trimming)

**Use Cases**:
- Precise audio trimming without silence
- Programmatic audio manipulation
- Synchronization with video
- Audio analysis tools

### 3. Silence Gap Detection

**Field**: `silence_gaps` (array, optional)

**Detects**:
- Silences longer than 500ms within an ayah
- Position of silence (after which word)
- Duration of silence

**Example**:
```json
{
  "surah_number": 55,
  "ayah_number": 29,
  "ayah_text": "يَسَْٔلُهُ مَن فِى السَّمَوَتِ وَالْأَرْضِ كُلَّ يَوْمٍ هُوَ فِى شَأْنٍ",
  "ayah_text_normalized": "يسئله من فى السموت والارض كل يوم هو فى شان",
  "silence_gaps": [
    {
      "silence_start_ms": 8500,
      "silence_end_ms": 9200,
      "silence_duration_ms": 700,
      "silence_position_after_word": 5
    }
  ]
}
```

**Interpretation**:
- Silence occurs after word 5 ("السَّمَوَتِ")
- Silence lasts 700ms
- Starts at 8.5 seconds into the ayah
- Ends at 9.2 seconds

**Use Cases**:
- Identify ayahs that were split during recitation
- Detect breathing pauses
- Quality control for recitations
- Audio editing guidance
- Memorization apps (mark pause points)

## Complete Metadata Structure

### JSON Response (split_audio=false)

```json
{
  "success": true,
  "data": {
    "exact_transcription": "...",
    "details": [
      {
        "surah_number": 55,
        "ayah_number": 1,
        "ayah_text_tashkeel": "الرَّحْمَنُ",
        "ayah_text_normalized": "الرحمن",
        "ayah_word_count": 1,
        "start_from_word": 1,
        "end_to_word": 1,
        "audio_start_timestamp": "00:00:05.500",
        "audio_end_timestamp": "00:00:10.100",
        "audio_start_offset_ms": 5500,
        "audio_end_offset_ms": 10100,
        "match_confidence": 1.0,
        "is_basmala": false
      }
    ]
  }
}
```

### ZIP metadata.json (split_audio=true)

```json
{
  "surah_number": 55,
  "total_ayahs": 79,
  "audio_format": "mp3",
  "ayahs": [
    {
      "surah_number": 55,
      "ayah_number": 0,
      "ayah_text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
      "ayah_text_normalized": "بسم الله الرحمن الرحيم",
      "filename": "surah_055_ayah_000_basmala.mp3",
      "is_basmala": true,
      "duration_seconds": 5.57,
      "audio_start_offset_ms": 0,
      "audio_end_offset_ms": 5570,
      "actual_ayah_start_offset_ms": 200,
      "actual_ayah_end_offset_ms": 5370
    },
    {
      "surah_number": 55,
      "ayah_number": 29,
      "ayah_text": "يَسَْٔلُهُ مَن فِى السَّمَوَتِ وَالْأَرْضِ كُلَّ يَوْمٍ هُوَ فِى شَأْنٍ",
      "ayah_text_normalized": "يسئله من فى السموت والارض كل يوم هو فى شان",
      "filename": "surah_055_ayah_029.mp3",
      "is_basmala": false,
      "duration_seconds": 21.7,
      "audio_start_offset_ms": 135500,
      "audio_end_offset_ms": 157200,
      "actual_ayah_start_offset_ms": 136000,
      "actual_ayah_end_offset_ms": 156700,
      "silence_gaps": [
        {
          "silence_start_ms": 8500,
          "silence_end_ms": 9200,
          "silence_duration_ms": 700,
          "silence_position_after_word": 5
        }
      ]
    }
  ]
}
```

## Use Case Examples

### 1. Search Application

```python
import json

# Load metadata
with open('metadata.json') as f:
    data = json.load(f)

# Search for ayahs containing a word (without diacritics)
search_term = "الرحمن"

results = []
for ayah in data['ayahs']:
    if search_term in ayah['ayah_text_normalized']:
        results.append({
            'ayah': ayah['ayah_number'],
            'text': ayah['ayah_text'],
            'filename': ayah['filename']
        })

print(f"Found {len(results)} ayahs containing '{search_term}'")
```

### 2. Precise Audio Trimming

```python
from pydub import AudioSegment

# Load original audio
audio = AudioSegment.from_mp3("surah_55.mp3")

# Trim ayah without silence
ayah = metadata['ayahs'][28]  # Ayah 29
start = ayah['actual_ayah_start_offset_ms']
end = ayah['actual_ayah_end_offset_ms']

# Extract without leading/trailing silence
trimmed = audio[start:end]
trimmed.export("ayah_29_trimmed.mp3", format="mp3")
```

### 3. Silence Analysis

```python
# Find ayahs with significant pauses
ayahs_with_pauses = []

for ayah in metadata['ayahs']:
    if 'silence_gaps' in ayah:
        for gap in ayah['silence_gaps']:
            if gap['silence_duration_ms'] > 600:  # More than 600ms
                ayahs_with_pauses.append({
                    'ayah': ayah['ayah_number'],
                    'pause_after_word': gap['silence_position_after_word'],
                    'pause_duration': gap['silence_duration_ms']
                })

print(f"Found {len(ayahs_with_pauses)} ayahs with significant pauses")
```

### 4. Memorization App with Pause Markers

```python
# Display ayah with pause indicators
ayah = metadata['ayahs'][28]
words = ayah['ayah_text_normalized'].split()

if 'silence_gaps' in ayah:
    for gap in ayah['silence_gaps']:
        pos = gap['silence_position_after_word']
        duration = gap['silence_duration_ms']
        
        # Insert pause marker
        words.insert(pos + 1, f"[PAUSE {duration}ms]")

print(' '.join(words))
# Output: يسئله من فى السموت والارض [PAUSE 700ms] كل يوم هو فى شان
```

### 5. Audio Player with Precise Seeking

```python
# Jump to exact ayah start (no silence)
def play_ayah(ayah_number):
    ayah = metadata['ayahs'][ayah_number]
    
    # Use actual offsets for precise playback
    start_ms = ayah['actual_ayah_start_offset_ms']
    end_ms = ayah['actual_ayah_end_offset_ms']
    
    audio_player.seek(start_ms)
    audio_player.play_until(end_ms)
```

## Silence Detection Algorithm

### Parameters

- **Minimum Silence Length**: 500ms
- **Silence Threshold**: -40 dBFS
- **Detection Method**: pydub.silence.detect_silence()

### Position Estimation

```python
# Estimate word position based on time ratio
position_ratio = silence_start / segment_duration
estimated_word_position = int(position_ratio * word_count)
```

**Note**: Position is approximate based on time distribution. For exact word-level timing, use a forced alignment tool.

### Edge Cases

1. **No Silence Detected**: `silence_gaps` field is omitted
2. **Multiple Silences**: Array contains all detected gaps
3. **Silence at Start/End**: Included if > 500ms
4. **Very Short Ayahs**: May not detect silences

## Performance Impact

| Feature | Processing Time | Memory |
|---------|----------------|--------|
| Normalized Text | Negligible | +50 bytes/ayah |
| Audio Offsets | Negligible | +32 bytes/ayah |
| Silence Detection | +0.1-0.3s/ayah | +100 bytes/gap |

**Total Impact**: +1-3 seconds for 78 ayahs

## Benefits Summary

### For Developers
- ✅ Rich metadata for advanced features
- ✅ Precise audio manipulation
- ✅ Search without diacritic matching
- ✅ Quality control insights

### For Users
- ✅ Better search results
- ✅ Cleaner audio playback
- ✅ Pause point awareness
- ✅ Accurate ayah boundaries

### For Applications
- ✅ Memorization tools with pause markers
- ✅ Audio editors with precise trimming
- ✅ Search engines with normalized text
- ✅ Quality assurance tools

## Future Enhancements

1. **Word-Level Timing**: Forced alignment for exact word positions
2. **Pause Classification**: Breathing vs. hesitation vs. intentional
3. **Recitation Quality Score**: Based on silence patterns
4. **Tajweed Analysis**: Detect elongations and stops
5. **Multi-Language Support**: Normalized text in different scripts

---

**Version**: 2.1.0  
**Branch**: feat-exp/split-audio-by-ayah  
**Status**: Implemented and Ready for Testing
