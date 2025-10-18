# Inference Module Documentation

**Date:** 2025-10-18  
**Status:** Complete

## Overview

The transcription service has been moved to a new **inference module** to support multiple machine learning models in the new algorithm.

## Changes Made

### File Moved
- **Old location:** `app/transcription_service.py`
- **New location:** `app/inference/transcription.py`

### New Module Structure

```
app/inference/
├── __init__.py           # Module exports
└── transcription.py      # Whisper transcription service
```

### Import Changes

**Old import:**
```python
from app.transcription_service import transcription_service
```

**New import:**
```python
from app.inference.transcription import transcription_service
# or
from app.inference import transcription_service
```

## Updated Files

### 1. **`app/queue/worker.py`** ✅
Updated import to use new path:
```python
from app.inference.transcription import transcription_service
```

### 2. **`app/inference/__init__.py`** ✅ (New)
Exports transcription service:
```python
from app.inference.transcription import TranscriptionService, transcription_service

__all__ = ['TranscriptionService', 'transcription_service']
```

## Purpose

The inference module is designed to house all machine learning models used in the project:

### Current Models
- **Transcription Service** - Whisper model for audio transcription

### Future Models (Planned)
You can now add additional inference models to this module:

```
app/inference/
├── __init__.py
├── transcription.py       # Whisper model
├── verse_detection.py     # Verse detection model (future)
├── speaker_diarization.py # Speaker identification (future)
├── audio_enhancement.py   # Audio quality enhancement (future)
└── language_detection.py  # Language detection (future)
```

## Adding New Inference Models

To add a new inference model:

### 1. Create a new file in `app/inference/`

```python
# app/inference/verse_detection.py

import torch
from transformers import AutoModel

class VerseDetectionService:
    """Service for detecting verse boundaries in audio."""
    
    MODEL_NAME = "your-model-name"
    
    def __init__(self):
        self.model = None
        self.device = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the model."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModel.from_pretrained(self.MODEL_NAME)
        self.model.to(self.device)
    
    def detect_verses(self, audio_array, sample_rate):
        """Detect verse boundaries."""
        # Your implementation
        pass

# Singleton instance
verse_detection_service = VerseDetectionService()
```

### 2. Export from `app/inference/__init__.py`

```python
from app.inference.transcription import TranscriptionService, transcription_service
from app.inference.verse_detection import VerseDetectionService, verse_detection_service

__all__ = [
    'TranscriptionService', 
    'transcription_service',
    'VerseDetectionService',
    'verse_detection_service'
]
```

### 3. Use in pipeline steps

```python
# app/pipeline/steps/verse_detection.py

from app.inference import verse_detection_service

class VerseDetectionStep(PipelineStep):
    def process(self, context: PipelineContext) -> PipelineContext:
        audio = context.audio_array
        sample_rate = context.sample_rate
        
        # Use the inference service
        verse_boundaries = verse_detection_service.detect_verses(
            audio, 
            sample_rate
        )
        
        context.set('verse_boundaries', verse_boundaries)
        return context
```

## Benefits

### 1. **Organization**
All ML models are in one place, making them easy to find and manage.

### 2. **Separation of Concerns**
Inference logic is separate from:
- API layer
- Pipeline logic
- Business logic

### 3. **Reusability**
Models can be used across different pipeline steps or even outside the pipeline.

### 4. **Scalability**
Easy to add new models without cluttering the main app directory.

### 5. **Testing**
Each inference service can be tested independently.

## Example Usage

### In Pipeline Steps

```python
from app.inference import transcription_service

# Use in a pipeline step
class MyStep(PipelineStep):
    def process(self, context):
        # Access model
        model = transcription_service.model
        processor = transcription_service.processor
        device = transcription_service.device
        
        # Use for inference
        result = model.generate(...)
        
        return context
```

### Direct Usage

```python
from app.inference import transcription_service

# Get model info
info = transcription_service.get_model_info()
print(f"Model: {info['model_name']}")
print(f"Device: {info['device']}")
```

## Model Management Best Practices

### 1. **Lazy Loading**
Load models only when needed:
```python
class MyService:
    def __init__(self):
        self.model = None
    
    def _ensure_model_loaded(self):
        if self.model is None:
            self._initialize_model()
```

### 2. **Singleton Pattern**
Use singleton instances to avoid loading models multiple times:
```python
# At module level
my_service = MyService()
```

### 3. **Device Management**
Always check for GPU availability:
```python
self.device = "cuda" if torch.cuda.is_available() else "cpu"
```

### 4. **Memory Management**
Clear GPU memory when needed:
```python
import torch

def clear_cache(self):
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

### 5. **Model Configuration**
Use config files or environment variables:
```python
import os

MODEL_NAME = os.getenv('TRANSCRIPTION_MODEL', 'tarteel-ai/whisper-base-ar-quran')
```

## Current Project Structure

```
app/
├── api/                    # HTTP endpoints
├── queue/                  # Job management
├── pipeline/               # Processing logic
├── inference/              # ✅ ML models (NEW)
│   ├── __init__.py
│   └── transcription.py
├── utils/                  # Utilities
├── database.py            # Database
└── main.py                # Entry point
```

## Migration Complete

✅ **Transcription service moved**  
✅ **Imports updated**  
✅ **Module structure created**  
✅ **Ready for additional models**  

The inference module is now ready to house all your machine learning models! 🚀

## Summary

The inference module provides:

- ✅ **Centralized model management**
- ✅ **Clean separation of concerns**
- ✅ **Easy to add new models**
- ✅ **Reusable across pipeline**
- ✅ **Better organization**
- ✅ **Scalable architecture**

You can now add additional inference models for your new algorithm!
