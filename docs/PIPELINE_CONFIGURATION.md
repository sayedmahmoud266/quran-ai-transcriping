# Pipeline Configuration Guide

This document explains how to configure the transcription pipeline using the flexible configuration system.

## Configuration Priority

The pipeline uses a **three-tier fallback system** for configuration values:

```
1. Function Parameter (Highest Priority)
   ↓
2. Environment Variable
   ↓
3. Default Value (Lowest Priority)
```

This gives you maximum flexibility:
- **Global defaults** via environment variables
- **Per-job overrides** via function parameters
- **Sensible fallbacks** when nothing is specified

## Configuration Methods

### Method 1: Use Defaults

Simply create the pipeline without any config:

```python
pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device
)
```

**Uses:** Built-in default values

### Method 2: Environment Variables (Global Config)

Set environment variables in `.env` file:

```bash
# .env
PIPELINE_TARGET_SAMPLE_RATE=16000
PIPELINE_MIN_SILENCE_LEN=500
PIPELINE_SILENCE_THRESH=-40
PIPELINE_KEEP_SILENCE=200
PIPELINE_MIN_CHUNK_DURATION=3.0
PIPELINE_MIN_SILENCE_GAP=0.5
```

Then create pipeline:

```python
pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device
)
```

**Uses:** Environment variables (global config for all jobs)

### Method 3: Function Parameters (Per-Job Config)

Pass config dictionary to override everything:

```python
config = {
    'min_silence_len': 300,  # Override for this job only
    'silence_thresh': -35
}

pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device,
    config=config
)
```

**Uses:** Passed config values, falls back to env vars or defaults

### Method 4: Mixed (Maximum Flexibility)

Combine all three methods:

```bash
# .env - Global defaults
PIPELINE_MIN_SILENCE_LEN=500
PIPELINE_SILENCE_THRESH=-40
```

```python
# Override specific values for this job
config = {
    'min_silence_len': 300  # Override env var for this job
    # silence_thresh will use env var (-40)
    # keep_silence will use default (200)
}

pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device,
    config=config
)
```

## Available Configuration Parameters

### Audio Resampling

| Parameter | Type | Default | Env Variable | Description |
|-----------|------|---------|--------------|-------------|
| `target_sample_rate` | int | 16000 | `PIPELINE_TARGET_SAMPLE_RATE` | Target sample rate for audio |

### Silence Detection

| Parameter | Type | Default | Env Variable | Description |
|-----------|------|---------|--------------|-------------|
| `min_silence_len` | int | 500 | `PIPELINE_MIN_SILENCE_LEN` | Minimum silence length in milliseconds |
| `silence_thresh` | int | -40 | `PIPELINE_SILENCE_THRESH` | Silence threshold in dBFS (negative value) |
| `keep_silence` | int | 200 | `PIPELINE_KEEP_SILENCE` | Silence padding to keep in milliseconds |

### Chunk Merging

| Parameter | Type | Default | Env Variable | Description |
|-----------|------|---------|--------------|-------------|
| `min_chunk_duration` | float | 3.0 | `PIPELINE_MIN_CHUNK_DURATION` | Minimum chunk duration in seconds |
| `min_silence_gap` | float | 0.5 | `PIPELINE_MIN_SILENCE_GAP` | Minimum silence gap between chunks in seconds |

## Examples

### Example 1: Development vs Production

**Development (.env.development):**
```bash
PIPELINE_MIN_SILENCE_LEN=300  # More aggressive splitting
PIPELINE_SILENCE_THRESH=-35   # More sensitive
```

**Production (.env.production):**
```bash
PIPELINE_MIN_SILENCE_LEN=500  # Conservative splitting
PIPELINE_SILENCE_THRESH=-40   # Less sensitive
```

### Example 2: Different Audio Types

**Clear studio recording:**
```python
config = {
    'min_silence_len': 500,
    'silence_thresh': -40,
    'min_chunk_duration': 5.0  # Longer chunks OK
}
```

**Noisy field recording:**
```python
config = {
    'min_silence_len': 300,
    'silence_thresh': -30,  # Higher threshold for noise
    'min_chunk_duration': 2.0  # Shorter chunks safer
}
```

### Example 3: Testing Different Settings

```python
# Test with different silence thresholds
for thresh in [-30, -35, -40, -45]:
    config = {'silence_thresh': thresh}
    
    pipeline = PipelineOrchestrator.create_full_pipeline(
        model=model,
        processor=processor,
        device=device,
        config=config
    )
    
    # Process and compare results
    context = PipelineOrchestrator.execute_pipeline(
        pipeline, audio, sample_rate
    )
```

### Example 4: User-Specific Settings

```python
# Load user preferences from database
user_config = get_user_pipeline_config(user_id)

# Apply user preferences
pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device,
    config=user_config
)
```

## Environment Variable Format

Environment variables are automatically parsed to the correct type:

| Type | Example | Parsed As |
|------|---------|-----------|
| `int` | `PIPELINE_MIN_SILENCE_LEN=500` | `500` (integer) |
| `float` | `PIPELINE_MIN_CHUNK_DURATION=3.5` | `3.5` (float) |
| `bool` | `PIPELINE_ENABLE_FEATURE=true` | `True` (boolean) |
| `str` | `PIPELINE_MODEL_NAME=whisper-base` | `"whisper-base"` (string) |

**Boolean values:** `true`, `1`, `yes`, `on` → `True`

## Configuration Validation

The pipeline logs the configuration values it uses:

```
INFO - Creating full transcription pipeline
DEBUG - AudioResamplingStep: target_sample_rate=16000
DEBUG - SilenceDetectionStep: min_silence_len=500, silence_thresh=-40, keep_silence=200
DEBUG - ChunkMergingStep: min_chunk_duration=3.0, min_silence_gap=0.5
```

Check the logs to verify your configuration is being applied correctly.

## Best Practices

### 1. Use Environment Variables for Defaults

Set sensible defaults in `.env` that work for most cases:

```bash
# .env
PIPELINE_MIN_SILENCE_LEN=500
PIPELINE_SILENCE_THRESH=-40
```

### 2. Override Only What You Need

Don't pass full config if you only need to change one value:

```python
# Good - Only override what's different
config = {'min_silence_len': 300}

# Avoid - Redundant full config
config = {
    'min_silence_len': 300,
    'silence_thresh': -40,  # Same as default
    'keep_silence': 200,    # Same as default
    # ...
}
```

### 3. Document Custom Configs

When using custom configs, document why:

```python
# Use shorter silence detection for this specific audio type
# because it has frequent pauses
config = {
    'min_silence_len': 300,
    'min_chunk_duration': 2.0
}
```

### 4. Test Configuration Changes

Always test with debug mode when changing configuration:

```bash
DEBUG_MODE=true
PIPELINE_MIN_SILENCE_LEN=300
```

Then check `.debug/{job_id}/` to verify the results.

### 5. Version Control Your .env.example

Create `.env.example` with documented defaults:

```bash
# .env.example

# Audio Resampling
PIPELINE_TARGET_SAMPLE_RATE=16000  # Hz

# Silence Detection
PIPELINE_MIN_SILENCE_LEN=500       # milliseconds
PIPELINE_SILENCE_THRESH=-40        # dBFS (negative)
PIPELINE_KEEP_SILENCE=200          # milliseconds

# Chunk Merging
PIPELINE_MIN_CHUNK_DURATION=3.0    # seconds
PIPELINE_MIN_SILENCE_GAP=0.5       # seconds
```

## Troubleshooting

### Config Not Applied

**Problem:** Environment variable not being used

**Solution:** 
1. Check `.env` file exists in project root
2. Verify `load_dotenv()` is called in `main.py`
3. Check variable name format: `PIPELINE_{KEY_UPPER}`
4. Restart the application

### Wrong Type Error

**Problem:** `Failed to parse env var PIPELINE_MIN_SILENCE_LEN=abc as int`

**Solution:** Ensure environment variable value is valid for its type:
```bash
# Wrong
PIPELINE_MIN_SILENCE_LEN=abc

# Correct
PIPELINE_MIN_SILENCE_LEN=500
```

### Config Precedence Confusion

**Problem:** Not sure which config value is being used

**Solution:** Check the debug logs:
```
DEBUG - SilenceDetectionStep: min_silence_len=500
```

Or add logging:
```python
config = {'min_silence_len': 300}
logger.info(f"Passed config: {config}")
```

## Advanced Usage

### Dynamic Configuration

Load configuration from external sources:

```python
# From database
config = load_config_from_db(job_id)

# From API
config = fetch_optimal_config(audio_characteristics)

# From file
import json
with open('config.json') as f:
    config = json.load(f)

pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device,
    config=config
)
```

### Configuration Profiles

Create configuration profiles for different scenarios:

```python
CONFIGS = {
    'fast': {
        'min_silence_len': 300,
        'min_chunk_duration': 2.0
    },
    'accurate': {
        'min_silence_len': 500,
        'min_chunk_duration': 5.0
    },
    'noisy': {
        'silence_thresh': -30,
        'min_silence_len': 400
    }
}

# Use profile
config = CONFIGS['accurate']
pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model, processor=processor, device=device, config=config
)
```

## Summary

✅ **Three-tier fallback:** Function param → Env var → Default  
✅ **Maximum flexibility:** Global and per-job configuration  
✅ **Type-safe:** Automatic type conversion  
✅ **Easy to use:** Works with or without configuration  
✅ **Well-documented:** Clear parameter descriptions  

The configuration system gives you complete control over pipeline behavior while maintaining simplicity for common use cases.
