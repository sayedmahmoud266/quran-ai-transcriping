# Debug Tools

This document describes the debugging tools available for analyzing pipeline execution.

## Debug Chunk Extractor

A simple tool to extract and save individual audio chunks from debug data.

### Purpose

When the pipeline processes audio, it splits it into chunks. This tool helps you:
- Extract individual chunk audio files
- Listen to each chunk separately
- Verify chunk boundaries are correct
- Debug silence detection and chunking logic

### Usage

```bash
python debug_chunk_extractor.py <step_folder_path>
```

### Example

```bash
# Extract chunks from SilenceDetectionStep
python debug_chunk_extractor.py .debug/6ad56078-e5dd-4f8a-9718-3b30e032a1eb/01_SilenceDetectionStep

# Extract chunks from any step that has chunks
python debug_chunk_extractor.py .debug/{job_id}/02_ChunkMergingStep
```

### What It Does

1. **Reads the debug data** from `data.json`
2. **Loads the audio** from `audio/audio.wav`
3. **Extracts chunks** based on timestamps in the data
4. **Saves individual files** to `extracted_chunks/` folder
5. **Creates a summary** in `chunks_summary.txt`

### Output Structure

```
01_SilenceDetectionStep/
├── data.json
├── timestamp.txt
├── audio/
│   └── audio.wav
└── extracted_chunks/              # ← Created by the tool
    ├── chunk_000_0.37s-7.88s.wav
    ├── chunk_001_11.24s-18.85s.wav
    ├── chunk_002_21.31s-26.54s.wav
    ├── ...
    └── chunks_summary.txt
```

### Chunk Filename Format

Chunks are named with their index and time range:
```
chunk_{index:03d}_{start}s-{end}s.wav
```

Examples:
- `chunk_000_0.37s-7.88s.wav` - First chunk from 0.37s to 7.88s
- `chunk_001_11.24s-18.85s.wav` - Second chunk from 11.24s to 18.85s

### Summary File

The tool creates `chunks_summary.txt` with:
- Step name
- Audio file info
- Sample rate
- Total duration
- List of all chunks with timestamps

Example:
```
Chunks Summary
============================================================

Step: 01_SilenceDetectionStep
Audio: audio.wav
Sample Rate: 16000Hz
Total Audio Duration: 80.35s
Number of Chunks: 8

Chunks:
------------------------------------------------------------
Chunk   0:    0.37s -    7.88s (  7.51s)
Chunk   1:   11.24s -   18.85s (  7.61s)
Chunk   2:   21.31s -   26.54s (  5.23s)
...
```

### Requirements

The tool requires:
- `numpy` - For audio array handling
- `soundfile` - For reading/writing WAV files

These are already in `requirements.txt`.

### Supported Data Formats

The tool handles different chunk data formats:

**Format 1** (used by SilenceDetectionStep):
```json
{
  "step_info": {
    "chunks": [
      {
        "chunk_index": 0,
        "start_time": 0.37,
        "end_time": 7.88,
        "duration": 7.51
      }
    ]
  }
}
```

**Format 2** (generic):
```json
{
  "chunks": [
    {
      "start": 0.37,
      "end": 7.88
    }
  ]
}
```

The tool automatically detects and handles both formats.

### Use Cases

#### 1. Verify Silence Detection
```bash
python debug_chunk_extractor.py .debug/{job_id}/01_SilenceDetectionStep
# Listen to extracted chunks to verify silence was detected correctly
```

#### 2. Check Chunk Merging
```bash
python debug_chunk_extractor.py .debug/{job_id}/02_ChunkMergingStep
# Compare chunks before and after merging
```

#### 3. Debug Transcription Issues
```bash
python debug_chunk_extractor.py .debug/{job_id}/03_ChunkTranscriptionStep
# Listen to chunks that failed transcription
```

### Troubleshooting

**No chunks found:**
- Check if the step actually produces chunks
- Verify `data.json` contains chunk data
- Look at the "Available keys" output to see what data exists

**Audio file not found:**
- Make sure the step saved audio data
- Check if `audio/` folder exists in the step directory

**Wrong chunk boundaries:**
- Verify the sample rate is correct
- Check if timestamps in data.json are accurate

### Tips

1. **Compare steps** - Extract chunks from multiple steps to see how they change
2. **Listen carefully** - Use the extracted chunks to verify audio quality
3. **Check boundaries** - Look for chunks that are too short or too long
4. **Verify silence** - Ensure silence periods are not included in chunks

## Future Tools

Additional debugging tools that could be added:

- **Transcription Viewer** - Display transcriptions with timestamps
- **Verse Matcher Debugger** - Visualize verse matching results
- **Pipeline Visualizer** - Generate flowchart of pipeline execution
- **Audio Comparator** - Compare audio at different pipeline stages

## Contributing

To add a new debug tool:

1. Create a new `.py` file in the project root
2. Make it executable: `chmod +x tool_name.py`
3. Add usage documentation to this README
4. Keep it simple and focused on one task
