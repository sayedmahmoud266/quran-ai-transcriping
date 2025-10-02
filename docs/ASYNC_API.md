# Async API Documentation

## Overview

The async API allows you to submit audio files for background processing, making the API more responsive for long-running transcription jobs. Instead of waiting for the entire transcription to complete, you receive a job ID immediately and can check the status later.

## Architecture

### Components

1. **SQLite Database** (`data/jobs.db`): Tracks job status and metadata
2. **Background Worker**: Processes jobs in FIFO order
3. **File Storage**:
   - `data/uploads/`: Uploaded audio files
   - `data/results/`: Generated zip files with ayah segments

### Job Lifecycle

```
1. Upload → 2. Queued → 3. Processing → 4. Completed/Failed
```

## API Endpoints

### 1. Submit Job (Async)

**Endpoint**: `POST /transcribe/async`

Upload an audio file for async processing.

**Request**:
```bash
curl -X POST "http://localhost:8000/transcribe/async" \
  -F "audio_file=@surah_12.mp3"
```

**Response**:
```json
{
  "success": true,
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "message": "Job queued for processing"
}
```

### 2. Check Job Status

**Endpoint**: `GET /jobs/{job_id}/status`

Check the current status of a job.

**Request**:
```bash
curl "http://localhost:8000/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/status"
```

**Response (Queued)**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "original_filename": "surah_12.mp3",
  "created_at": "2025-10-03T00:00:00",
  "started_at": null,
  "completed_at": null
}
```

**Response (Processing)**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "processing",
  "original_filename": "surah_12.mp3",
  "created_at": "2025-10-03T00:00:00",
  "started_at": "2025-10-03T00:00:15",
  "completed_at": null
}
```

**Response (Completed)**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "original_filename": "surah_12.mp3",
  "created_at": "2025-10-03T00:00:00",
  "started_at": "2025-10-03T00:00:15",
  "completed_at": "2025-10-03T00:02:30",
  "download_url": "/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download",
  "metadata_url": "/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metadata"
}
```

**Response (Failed)**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failed",
  "original_filename": "surah_12.mp3",
  "created_at": "2025-10-03T00:00:00",
  "started_at": "2025-10-03T00:00:15",
  "completed_at": "2025-10-03T00:00:45",
  "error": "Error message here"
}
```

### 3. Download Result

**Endpoint**: `GET /jobs/{job_id}/download`

Download the zip file containing ayah segments.

**Request**:
```bash
curl "http://localhost:8000/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download" \
  --output result.zip
```

**Response**: Binary zip file

### 4. Get Metadata Only

**Endpoint**: `GET /jobs/{job_id}/metadata`

Get only the JSON metadata without downloading the full zip.

**Request**:
```bash
curl "http://localhost:8000/jobs/a1b2c3d4-e5f6-7890-abcd-ef1234567890/metadata"
```

**Response**:
```json
{
  "surah_number": 12,
  "total_ayahs": 111,
  "transcription": "بسم الله الرحمن الرحيم...",
  "ayahs": [
    {
      "surah_number": 12,
      "ayah_number": 0,
      "ayah_text": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
      "filename": "surah_012_ayah_000_basmala.mp3",
      "is_basmala": true,
      "duration_seconds": 5.2,
      "cutoff_uncertain": false
    },
    ...
  ],
  "diagnostics": {
    "audio_input_end_timestamp": "00:20:15.000",
    "last_ayah_end_timestamp": "00:20:10.500",
    ...
  }
}
```

### 5. List All Jobs

**Endpoint**: `GET /jobs?limit=100`

List all jobs (most recent first).

**Request**:
```bash
curl "http://localhost:8000/jobs?limit=50"
```

**Response**:
```json
{
  "total": 3,
  "jobs": [
    {
      "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "original_filename": "surah_12.mp3",
      "status": "completed",
      "created_at": "2025-10-03T00:00:00",
      "completed_at": "2025-10-03T00:02:30"
    },
    {
      "job_id": "b2c3d4e5-f6g7-8901-bcde-fg2345678901",
      "original_filename": "surah_55.mp3",
      "status": "processing",
      "created_at": "2025-10-03T00:05:00",
      "completed_at": null
    },
    {
      "job_id": "c3d4e5f6-g7h8-9012-cdef-gh3456789012",
      "original_filename": "surah_18.mp3",
      "status": "queued",
      "created_at": "2025-10-03T00:10:00",
      "completed_at": null
    }
  ]
}
```

## Usage Examples

### Python Example

```python
import requests
import time

# 1. Submit job
with open('surah_12.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/transcribe/async',
        files={'audio_file': f}
    )
    job_id = response.json()['job_id']
    print(f"Job submitted: {job_id}")

# 2. Poll for completion
while True:
    status_response = requests.get(
        f'http://localhost:8000/jobs/{job_id}/status'
    )
    status = status_response.json()['status']
    print(f"Status: {status}")
    
    if status == 'completed':
        break
    elif status == 'failed':
        print(f"Error: {status_response.json()['error']}")
        exit(1)
    
    time.sleep(5)  # Check every 5 seconds

# 3. Download result
download_response = requests.get(
    f'http://localhost:8000/jobs/{job_id}/download'
)
with open('result.zip', 'wb') as f:
    f.write(download_response.content)
print("Downloaded result.zip")

# 4. Get metadata
metadata_response = requests.get(
    f'http://localhost:8000/jobs/{job_id}/metadata'
)
metadata = metadata_response.json()
print(f"Surah {metadata['surah_number']}: {metadata['total_ayahs']} ayahs")
```

### JavaScript Example

```javascript
// 1. Submit job
const formData = new FormData();
formData.append('audio_file', audioFile);

const submitResponse = await fetch('http://localhost:8000/transcribe/async', {
  method: 'POST',
  body: formData
});
const { job_id } = await submitResponse.json();
console.log(`Job submitted: ${job_id}`);

// 2. Poll for completion
async function pollStatus(jobId) {
  while (true) {
    const statusResponse = await fetch(
      `http://localhost:8000/jobs/${jobId}/status`
    );
    const status = await statusResponse.json();
    console.log(`Status: ${status.status}`);
    
    if (status.status === 'completed') {
      return status;
    } else if (status.status === 'failed') {
      throw new Error(status.error);
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

const completedStatus = await pollStatus(job_id);

// 3. Download result
const downloadUrl = `http://localhost:8000/jobs/${job_id}/download`;
window.location.href = downloadUrl;

// 4. Get metadata
const metadataResponse = await fetch(
  `http://localhost:8000/jobs/${job_id}/metadata`
);
const metadata = await metadataResponse.json();
console.log(`Surah ${metadata.surah_number}: ${metadata.total_ayahs} ayahs`);
```

## Job Status Flow

```
QUEUED → PROCESSING → COMPLETED
                   ↘ FAILED
```

- **queued**: Job is waiting in queue
- **processing**: Job is currently being processed
- **completed**: Job finished successfully, results available
- **failed**: Job failed with error

## Background Worker

The background worker:
- Runs in a separate thread
- Processes jobs in FIFO order
- Automatically starts on API startup
- Processes one job at a time
- Checks for new jobs every 2 seconds when idle

## Database Schema

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,              -- UUID
    original_filename TEXT NOT NULL,
    audio_file_path TEXT NOT NULL,
    status TEXT NOT NULL,             -- queued/processing/completed/failed
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    result_zip_path TEXT,
    metadata_json TEXT,
    transcription_text TEXT
);
```

## File Storage

### Uploads Directory
- Location: `data/uploads/`
- Files: `{uuid}.{ext}`
- Kept after processing for potential reprocessing

### Results Directory
- Location: `data/results/`
- Files: `{job_id}.zip`
- Contains ayah segments and metadata

## Performance

| Metric | Value |
|--------|-------|
| **Upload Time** | < 1 second |
| **Queue Response** | Immediate |
| **Processing Time** | 20-120 seconds (depends on audio length) |
| **Concurrent Jobs** | 1 (sequential processing) |

## Error Handling

### Common Errors

**404 - Job Not Found**
```json
{
  "detail": "Job not found"
}
```

**400 - Job Not Completed**
```json
{
  "detail": "Job is not completed yet. Current status: processing"
}
```

**400 - Unsupported Format**
```json
{
  "detail": "Unsupported audio format: .xyz"
}
```

## Migration from Sync API

### Before (Sync)
```python
response = requests.post(
    'http://localhost:8000/transcribe',
    files={'audio_file': open('surah.mp3', 'rb')},
    data={'split_audio': 'true'}
)
# Waits for entire processing...
with open('result.zip', 'wb') as f:
    f.write(response.content)
```

### After (Async)
```python
# Submit and get job_id immediately
response = requests.post(
    'http://localhost:8000/transcribe/async',
    files={'audio_file': open('surah.mp3', 'rb')}
)
job_id = response.json()['job_id']

# Check status later
# Download when ready
```

## Benefits

✅ **Immediate Response**: No waiting for long processing  
✅ **Better UX**: Users can do other things while processing  
✅ **Scalable**: Can handle multiple requests  
✅ **Reliable**: Jobs tracked in database  
✅ **Flexible**: Check status anytime, download anytime  

## Limitations

- Single worker (processes one job at a time)
- No job cancellation (yet)
- No job priority system (FIFO only)
- No automatic cleanup of old jobs

## Future Enhancements

- [ ] Multiple workers for parallel processing
- [ ] Job cancellation endpoint
- [ ] Priority queue system
- [ ] Automatic cleanup of old jobs
- [ ] WebSocket for real-time status updates
- [ ] Progress percentage during processing

---

**Version**: 2.2.0  
**Last Updated**: October 2025
