# Debug Mode Documentation

## Overview

Debug mode provides comprehensive logging of the entire audio processing pipeline, saving data and audio files at each step for analysis and troubleshooting.

## Enabling Debug Mode

Set the `DEBUG_MODE` environment variable to enable debug recording:

```bash
export DEBUG_MODE=true
```

Or in your `.env` file:
```
DEBUG_MODE=true
```

Accepted values: `true`, `1`, `yes` (case-insensitive)

## Debug Output Structure

When debug mode is enabled, a folder is created for each job:

```
.debug/
└── {job_id}/
    ├── 01_audio_resampled/
    │   ├── timestamp.txt
    │   ├── data.json
    │   └── audio/
    │       └── resampled_audio.wav
    ├── 02_silence_detected/
    │   ├── timestamp.txt
    │   ├── data.json
    │   └── audio/
    │       ├── chunk_000.wav
    │       ├── chunk_001.wav
    │       └── ...
    ├── 03_chunks_merged/
    ├── 04_chunks_transcribed/
    ├── 05_duplicates_removed/
    ├── 06_timestamps_combined/
    ├── 07_verses_matched/
    ├── 08_timestamps_calculated/
    ├── 09_before_silence_splitting/
    ├── 10_after_silence_splitting/
    ├── 11_before_audio_splitting/
    └── 12_after_audio_splitting/
```

## Processing Steps

### 1. Audio Resampled
**Location**: `01_audio_resampled/`

**Contains**:
- Full resampled audio file (16kHz, mono)
- Metadata: sample rate, duration, total samples

**Purpose**: Verify audio loading and resampling

---

### 2. Silence Detected
**Location**: `02_silence_detected/`

**Contains**:
- All detected non-silent audio chunks
- Metadata: chunk count, start/end times, durations

**Purpose**: Analyze silence detection accuracy

---

### 3. Chunks Merged
**Location**: `03_chunks_merged/`

**Contains**:
- Merged audio chunks (< 3 seconds combined)
- Metadata: original vs merged chunk counts

**Purpose**: Verify chunk merging logic

---

### 4. Chunks Transcribed
**Location**: `04_chunks_transcribed/`

**Contains**:
- Audio files for each transcribed chunk
- Metadata: transcribed text, word counts, timestamps per chunk

**Purpose**: Verify transcription accuracy per chunk

---

### 5. Duplicates Removed
**Location**: `05_duplicates_removed/`

**Contains**:
- JSON data showing:
  - Original text per chunk
  - Deduplicated text per chunk
  - Word counts before/after
  - Total duplicates removed

**Purpose**: Verify duplicate word removal between chunks

---

### 6. Timestamps Combined
**Location**: `06_timestamps_combined/`

**Contains**:
- Combined transcription text
- Word-level timestamps (first 100 for brevity)

**Purpose**: Verify timestamp combination logic

---

### 7. Verses Matched
**Location**: `07_verses_matched/`

**Contains**:
- Matched verses from PyQuran
- Ayah-to-chunk mapping
- Chunk-to-ayah mapping

**Purpose**: Verify verse matching accuracy

---

### 8. Timestamps Calculated
**Location**: `08_timestamps_calculated/`

**Contains**:
- Calculated timestamps for each ayah
- Chunk mapping details per ayah
- Scenario used for each ayah (1-4)

**Purpose**: Verify timestamp calculation logic

---

### 9. Before Silence Splitting
**Location**: `09_before_silence_splitting/`

**Contains**:
- Ayah timestamps before silence adjustment

**Purpose**: Compare timestamps before/after silence splitting

---

### 10. After Silence Splitting
**Location**: `10_after_silence_splitting/`

**Contains**:
- Ayah timestamps after silence adjustment
- Shows which silences were split

**Purpose**: Verify silence splitting logic

---

### 11. Before Audio Splitting
**Location**: `11_before_audio_splitting/`

**Contains**:
- Final ayah details before splitting
- Audio duration and ayah count

**Purpose**: Final verification before audio splitting

---

### 12. After Audio Splitting
**Location**: `12_after_audio_splitting/`

**Contains**:
- Individual ayah audio files
- Metadata: filenames, durations
- Final zip file information

**Purpose**: Verify final audio splitting results

---

## File Formats

### timestamp.txt
Contains ISO format timestamp of when the step was executed:
```
2025-10-07T00:30:15.123456
```

### data.json
Contains step-specific data in JSON format with UTF-8 encoding:
```json
{
  "total_chunks": 10,
  "chunks": [...]
}
```

### audio/*.wav
Audio files in WAV format (16kHz, mono, float32)

---

## Usage Examples

### Example 1: Debugging Transcription Issues

1. Enable debug mode
2. Process a problematic audio file
3. Check `04_chunks_transcribed/data.json` for transcription text
4. Listen to chunk audio files to verify accuracy

### Example 2: Analyzing Timestamp Accuracy

1. Enable debug mode
2. Process audio
3. Compare timestamps in:
   - `08_timestamps_calculated/` (calculated)
   - `09_before_silence_splitting/` (before adjustment)
   - `10_after_silence_splitting/` (final)
4. Check `12_after_audio_splitting/` audio files

### Example 3: Investigating Duplicate Removal

1. Enable debug mode
2. Process audio
3. Check `04_chunks_transcribed/data.json` for original text
4. Check `05_duplicates_removed/data.json` for deduplicated text
5. Verify duplicates were correctly identified

---

## Performance Impact

**Storage**: Each job generates approximately 50-200 MB of debug data depending on audio length

**Processing Time**: Minimal impact (~1-2% slower) due to file I/O

**Recommendation**: Only enable debug mode when troubleshooting or analyzing specific jobs

---

## Cleanup

Debug data is not automatically deleted. To clean up:

```bash
# Remove all debug data
rm -rf .debug/

# Remove specific job debug data
rm -rf .debug/{job_id}
```

---

## Integration with Logging

Debug mode integrates with the standard logging system. When enabled, you'll see:

```
INFO: [job_id] Debug mode enabled - data will be saved to .debug/{job_id}
INFO: Debug: Saved step '01_audio_resampled' to .debug/{job_id}/01_audio_resampled
...
INFO: Debug data for job {job_id}:
Location: .debug/{job_id}
Steps recorded:
  - 01_audio_resampled: 3 files
  - 02_silence_detected: 15 files
  ...
```

---

## Troubleshooting

### Debug files not being created

- Verify `DEBUG_MODE=true` is set
- Check file permissions on `.debug/` directory
- Check logs for debug-related errors

### Missing audio files

- Ensure sufficient disk space
- Check that audio data is valid (not empty)
- Verify sample rate is correct

### Large debug folders

- Debug data accumulates over time
- Regularly clean up old debug folders
- Consider selective debugging (enable only for specific jobs)

---

## Best Practices

1. **Enable selectively**: Only use debug mode when needed
2. **Clean regularly**: Remove old debug data to save disk space
3. **Document findings**: Note any issues discovered through debug data
4. **Share debug data**: Include relevant debug files when reporting issues
5. **Verify steps**: Check each step sequentially when troubleshooting

---

## Technical Details

### Implementation

- **Module**: `app/debug_utils.py`
- **Class**: `DebugRecorder`
- **Integration**: Set via module-level functions in each processor

### Thread Safety

Debug recorder is set per-job and cleared after processing, ensuring thread safety in the background worker.

### Audio Format

All audio files are saved as:
- Format: WAV
- Sample Rate: 16kHz (or original rate where applicable)
- Channels: Mono
- Bit Depth: 32-bit float

---

## Future Enhancements

Potential improvements to debug mode:

- [ ] Configurable debug levels (minimal, standard, verbose)
- [ ] Automatic cleanup of old debug data
- [ ] Debug data compression
- [ ] Web UI for browsing debug data
- [ ] Comparative analysis tools
- [ ] Export debug reports

---

**Last Updated**: 2025-10-07
**Version**: 1.0.0
