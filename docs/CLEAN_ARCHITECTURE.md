# Clean Architecture Documentation

**Version:** 2.0  
**Date:** 2025-10-18  
**Status:** Production Ready

## Overview

The Quran AI project has been refactored to follow **Clean Architecture** principles with clear separation of concerns. The architecture is organized into distinct modules, each with a single responsibility.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                             │
│                  (HTTP Endpoints Only)                       │
│                    app/api/routes.py                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     Queue Module                             │
│              (Job Management & Worker)                       │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │   JobQueue       │         │ BackgroundWorker │         │
│  │ (Job Lifecycle)  │◄────────┤  (Processing)    │         │
│  └──────────────────┘         └──────────────────┘         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Pipeline Module                            │
│              (Processing Steps & Logic)                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PipelineOrchestrator → Pipeline → PipelineSteps     │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Utility Modules                           │
│         (Audio Loading, Splitting, Debug, etc.)              │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐           │
│  │AudioLoader │  │AudioSplitter│  │DebugUtils  │           │
│  └────────────┘  └────────────┘  └────────────┘           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Core Services                               │
│         (Model, Database, Quran Data)                        │
│                                                              │
│  ┌──────────────┐  ┌──────────┐  ┌──────────────┐         │
│  │Transcription │  │ Database │  │  QuranData   │         │
│  │   Service    │  │          │  │              │         │
│  └──────────────┘  └──────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

### 1. API Module (`app/api/`)

**Responsibility:** HTTP endpoints and request/response handling only.

**Files:**
- `routes.py` - All FastAPI endpoints

**What it does:**
- ✅ Handle HTTP requests
- ✅ Validate request parameters
- ✅ Call job queue operations
- ✅ Return HTTP responses
- ✅ Serve files (ZIP downloads)

**What it does NOT do:**
- ❌ Process audio
- ❌ Manage job lifecycle
- ❌ Execute pipeline
- ❌ Business logic

**Example:**
```python
@app.post("/transcribe/async")
async def transcribe_async(audio_file: UploadFile):
    # Save file
    saved_path = save_uploaded_file(audio_file)
    
    # Create job (delegates to queue module)
    job_id = job_queue.create_job(saved_path, audio_file.filename)
    
    # Return response
    return {"job_id": job_id, "status": "queued"}
```

### 2. Queue Module (`app/queue/`)

**Responsibility:** Job management and background processing.

**Files:**
- `job_queue.py` - Job lifecycle management
- `worker.py` - Background worker thread

**What it does:**
- ✅ Create and track jobs
- ✅ Manage job queue
- ✅ Run background worker
- ✅ Execute pipeline for each job
- ✅ Update job status
- ✅ Handle job results

**What it does NOT do:**
- ❌ Handle HTTP requests
- ❌ Implement processing logic
- ❌ Define pipeline steps

**Example:**
```python
# JobQueue - manages job lifecycle
job_id = job_queue.create_job(audio_path, filename)
status = job_queue.get_job_status(job_id)
result = job_queue.get_job_result_path(job_id)

# BackgroundWorker - processes jobs
background_worker.start()  # Starts processing thread
# Worker automatically picks up jobs and runs pipeline
```

### 3. Pipeline Module (`app/pipeline/`)

**Responsibility:** Audio processing logic and workflow.

**Files:**
- `base.py` - Core abstractions (PipelineStep, Pipeline, PipelineContext)
- `orchestrator.py` - Pipeline factory and execution
- `steps/` - Individual processing steps

**What it does:**
- ✅ Define processing steps
- ✅ Execute workflow
- ✅ Manage data flow between steps
- ✅ Track execution metrics
- ✅ Handle errors in processing

**What it does NOT do:**
- ❌ Manage jobs
- ❌ Handle HTTP requests
- ❌ Persist data

**Example:**
```python
# Create pipeline
pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device,
    quran_data=quran_data
)

# Execute pipeline
context = PipelineOrchestrator.execute_pipeline(
    pipeline=pipeline,
    audio_array=audio,
    sample_rate=16000
)

# Get results
transcription = context.final_transcription
verses = context.verse_details
```

### 4. Utility Module (`app/utils/`)

**Responsibility:** Reusable utility functions.

**Files:**
- `audio_loader.py` - Audio file loading
- `audio_splitter.py` - Audio splitting by verses
- `debug_utils.py` - Debug recording

**What it does:**
- ✅ Load audio files
- ✅ Split audio by timestamps
- ✅ Debug recording
- ✅ Helper functions

**What it does NOT do:**
- ❌ Business logic
- ❌ Job management
- ❌ HTTP handling

### 5. Core Services (`app/`)

**Responsibility:** Core business services and data access.

**Files:**
- `transcription_service.py` - Whisper model management
- `database.py` - Database operations
- `quran_data.py` - Quran text and data

**What they do:**
- ✅ Initialize and manage Whisper model
- ✅ Database CRUD operations
- ✅ Load Quran text
- ✅ Text normalization

## Data Flow

### Job Submission Flow

```
1. User uploads file via API
   └─> POST /transcribe/async

2. API saves file and creates job
   └─> job_queue.create_job()

3. Job added to database with QUEUED status
   └─> database.create_job()

4. Worker picks up job
   └─> background_worker._process_job()

5. Worker loads audio
   └─> load_audio_file()

6. Worker creates and executes pipeline
   └─> PipelineOrchestrator.create_full_pipeline()
   └─> PipelineOrchestrator.execute_pipeline()

7. Pipeline processes audio through 10 steps
   └─> AudioResamplingStep
   └─> SilenceDetectionStep
   └─> ... (8 more steps)

8. Worker saves results
   └─> split_audio_by_ayahs()
   └─> Save ZIP file

9. Worker updates job status to COMPLETED
   └─> job_queue.update_job_status()

10. User retrieves results via API
    └─> GET /jobs/{job_id}/download
```

### Job Status Check Flow

```
1. User checks status
   └─> GET /jobs/{job_id}/status

2. API queries job queue
   └─> job_queue.get_job()

3. Job queue queries database
   └─> database.get_job()

4. API returns status
   └─> {status: "processing", ...}
```

## File Organization

```
app/
├── api/                    # API Layer
│   ├── __init__.py
│   └── routes.py          # FastAPI endpoints
│
├── queue/                  # Queue Module
│   ├── __init__.py
│   ├── job_queue.py       # Job management
│   └── worker.py          # Background worker
│
├── pipeline/               # Pipeline Module
│   ├── __init__.py
│   ├── base.py            # Core abstractions
│   ├── orchestrator.py    # Pipeline factory
│   └── steps/             # Processing steps
│       ├── __init__.py
│       ├── audio_resampling.py
│       ├── silence_detection.py
│       ├── chunk_merging.py
│       ├── chunk_transcription.py
│       ├── duplicate_removal.py
│       ├── transcription_combining.py
│       ├── verse_matching.py
│       ├── timestamp_calculation.py
│       ├── silence_splitting.py
│       └── audio_splitting.py
│
├── utils/                  # Utility Module
│   ├── __init__.py
│   ├── audio_loader.py    # Audio loading
│   ├── audio_splitter.py  # Audio splitting
│   └── debug_utils.py     # Debug utilities
│
├── database.py             # Database service
├── quran_data.py          # Quran data service
├── transcription_service.py  # Model service
└── main_new.py            # Application entry point
```

## Key Principles

### 1. Separation of Concerns

Each module has a single, well-defined responsibility:
- **API** → HTTP only
- **Queue** → Job management only
- **Pipeline** → Processing logic only
- **Utils** → Reusable helpers only

### 2. Dependency Direction

Dependencies flow inward:
```
API → Queue → Pipeline → Utils → Core Services
```

Outer layers depend on inner layers, never the reverse.

### 3. Interface Segregation

Each module exposes a clean interface:
```python
# API exposes HTTP endpoints
POST /transcribe/async
GET /jobs/{id}/status

# Queue exposes job operations
job_queue.create_job()
job_queue.get_job_status()

# Pipeline exposes execution
PipelineOrchestrator.execute_pipeline()
```

### 4. Single Responsibility

Each class/module does one thing:
- `JobQueue` → Manages job lifecycle
- `BackgroundWorker` → Processes jobs
- `Pipeline` → Executes steps
- `PipelineStep` → Performs one processing task

### 5. Open/Closed Principle

Easy to extend without modifying:
```python
# Add new pipeline step
class MyNewStep(PipelineStep):
    def process(self, context):
        # Implementation
        pass

# Add to pipeline
pipeline.add_step(MyNewStep())
```

## Benefits

### 1. **Testability**
Each module can be tested independently:
```python
# Test API without worker
def test_api_create_job():
    response = client.post("/transcribe/async", files={"audio_file": file})
    assert response.status_code == 200

# Test pipeline without API
def test_pipeline_execution():
    context = pipeline.execute(initial_context)
    assert context.final_transcription
```

### 2. **Maintainability**
Clear boundaries make changes easier:
- Change API endpoints → Only modify `app/api/routes.py`
- Change processing logic → Only modify pipeline steps
- Change job storage → Only modify `database.py`

### 3. **Scalability**
Easy to scale components independently:
- Scale API → Add more API servers
- Scale workers → Add more worker processes
- Scale pipeline → Optimize individual steps

### 4. **Flexibility**
Easy to swap implementations:
- Replace FastAPI with Flask → Only change API module
- Replace SQLite with PostgreSQL → Only change database module
- Replace pipeline → Only change pipeline module

## Migration Guide

### Old Code
```python
# Old monolithic approach
from app.main import app
from app.transcription_service import transcription_service

result = transcription_service.transcribe_audio(audio, sr)
```

### New Code
```python
# New clean architecture
from app.main_new import app
from app.queue.job_queue import job_queue

# Create job
job_id = job_queue.create_job(audio_path, filename)

# Check status
status = job_queue.get_job_status(job_id)

# Get results
result_path = job_queue.get_job_result_path(job_id)
```

## Usage Examples

### Starting the Application

```bash
# Using new main file
python -m app.main_new

# Or with uvicorn
uvicorn app.main_new:app --host 0.0.0.0 --port 8000
```

### API Usage

```bash
# Submit job
curl -X POST "http://localhost:8000/transcribe/async" \
  -F "audio_file=@audio.mp3"

# Check status
curl "http://localhost:8000/jobs/{job_id}/status"

# Download result
curl "http://localhost:8000/jobs/{job_id}/download" -o result.zip
```

### Programmatic Usage

```python
from app.queue.job_queue import job_queue
from app.queue.worker import background_worker

# Start worker
background_worker.start()

# Create job
job_id = job_queue.create_job("/path/to/audio.mp3", "audio.mp3")

# Wait for completion
import time
while not job_queue.is_job_complete(job_id):
    time.sleep(1)

# Get results
result_path = job_queue.get_job_result_path(job_id)
metadata = job_queue.get_job_metadata(job_id)
```

## Testing Strategy

### Unit Tests
```python
# Test individual components
def test_job_queue_create():
    job_id = job_queue.create_job("path", "file.mp3")
    assert job_id

def test_pipeline_step():
    step = AudioResamplingStep()
    context = step.execute(initial_context)
    assert context.sample_rate == 16000
```

### Integration Tests
```python
# Test module interactions
def test_worker_processes_job():
    job_id = job_queue.create_job("path", "file.mp3")
    worker._process_job(job_queue.get_job(job_id))
    assert job_queue.is_job_complete(job_id)
```

### End-to-End Tests
```python
# Test full flow
def test_full_transcription_flow():
    # Submit via API
    response = client.post("/transcribe/async", files={"audio_file": file})
    job_id = response.json()["job_id"]
    
    # Wait for completion
    wait_for_job_completion(job_id)
    
    # Download result
    response = client.get(f"/jobs/{job_id}/download")
    assert response.status_code == 200
```

## Summary

The new clean architecture provides:

✅ **Clear Separation** - Each module has one responsibility  
✅ **Easy Testing** - Components can be tested independently  
✅ **Better Maintainability** - Changes are localized  
✅ **Improved Scalability** - Components can scale independently  
✅ **Flexible** - Easy to swap implementations  
✅ **Production Ready** - Follows industry best practices  

The architecture follows SOLID principles and makes the codebase more professional, maintainable, and scalable.
