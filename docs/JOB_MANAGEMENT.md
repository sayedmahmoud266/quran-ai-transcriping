# Job Management APIs

## Overview

This document describes the job management APIs for the Quran AI Transcription service. These APIs allow you to manage the job queue and clean up finished jobs.

## New Endpoints

### 1. Resume Job Queue

**Endpoint**: `POST /jobs/resume`

**Purpose**: Resume the job queue by restarting any jobs that are still in processing status.

**Use Cases**:
- Server was restarted while jobs were being processed
- Worker thread crashed and needs to be restarted
- Manual intervention to retry stuck jobs

**How It Works**:
1. Finds all jobs with status `processing`
2. Resets them to `queued` status
3. Clears their `started_at` timestamp
4. Triggers the background worker to start processing

**Request**:
```bash
curl -X POST "http://localhost:8000/jobs/resume"
```

**Response**:
```json
{
  "success": true,
  "message": "Job queue resumed. 2 processing job(s) reset to queued.",
  "jobs_reset": 2,
  "worker_running": true,
  "worker_processing": false
}
```

**Response Fields**:
- `success`: Boolean indicating if operation succeeded
- `message`: Human-readable message
- `jobs_reset`: Number of jobs that were reset from processing to queued
- `worker_running`: Whether the background worker is running
- `worker_processing`: Whether the worker is currently processing a job

---

### 2. Clear Finished Jobs

**Endpoint**: `DELETE /jobs/finished`

**Purpose**: Clear all finished jobs (completed or failed) from the database and remove their files.

**Use Cases**:
- Clean up disk space by removing old completed jobs
- Remove failed jobs after investigating errors
- Periodic maintenance to keep database clean

**What Gets Deleted**:
1. All jobs with status `completed` or `failed` from the database
2. Uploaded audio files from `data/uploads/`
3. Result zip files from `data/results/`

**Request**:
```bash
curl -X DELETE "http://localhost:8000/jobs/finished"
```

**Response (Jobs Cleared)**:
```json
{
  "success": true,
  "message": "Cleared 15 finished job(s) and removed 30 file(s)",
  "jobs_deleted": 15,
  "files_removed": 30
}
```

**Response (No Jobs)**:
```json
{
  "success": true,
  "message": "No finished jobs to clear",
  "jobs_deleted": 0,
  "files_removed": 0
}
```

**Response Fields**:
- `success`: Boolean indicating if operation succeeded
- `message`: Human-readable message
- `jobs_deleted`: Number of jobs deleted from database
- `files_removed`: Number of files removed from disk (audio + result files)

---

## Database Changes

### New Methods in `database.py`

#### `get_processing_jobs() -> List[Dict]`
Returns all jobs with status `processing`, ordered by `started_at` (oldest first).

#### `get_finished_jobs() -> List[Dict]`
Returns all jobs with status `completed` or `failed`, ordered by `completed_at` (newest first).

#### `reset_processing_jobs_to_queued() -> int`
Resets all `processing` jobs to `queued` status and clears their `started_at` timestamp. Returns the number of jobs reset.

---

## Usage Examples

### Python

```python
import requests

# Resume job queue after server restart
response = requests.post('http://localhost:8000/jobs/resume')
print(f"Jobs reset: {response.json()['jobs_reset']}")

# Clear all finished jobs
response = requests.delete('http://localhost:8000/jobs/finished')
print(f"Jobs deleted: {response.json()['jobs_deleted']}")
print(f"Files removed: {response.json()['files_removed']}")
```

### JavaScript

```javascript
// Resume job queue after server restart
const resumeResponse = await fetch('http://localhost:8000/jobs/resume', {
  method: 'POST'
});
const resumeData = await resumeResponse.json();
console.log(`Jobs reset: ${resumeData.jobs_reset}`);

// Clear all finished jobs
const clearResponse = await fetch('http://localhost:8000/jobs/finished', {
  method: 'DELETE'
});
const clearData = await clearResponse.json();
console.log(`Jobs deleted: ${clearData.jobs_deleted}`);
console.log(`Files removed: ${clearData.files_removed}`);
```

### cURL

```bash
# Resume job queue
curl -X POST "http://localhost:8000/jobs/resume"

# Clear finished jobs
curl -X DELETE "http://localhost:8000/jobs/finished"
```

---

## Best Practices

### Resume Job Queue

1. **After Server Restart**: Always call this endpoint after restarting the server to resume any interrupted jobs.
2. **Monitoring**: Check the `jobs_reset` count to see how many jobs were interrupted.
3. **Automation**: Consider adding this to your server startup script.

### Clear Finished Jobs

1. **Regular Maintenance**: Run this periodically to prevent disk space issues.
2. **Before Clearing**: Download any results you need before clearing finished jobs.
3. **Failed Jobs**: Review error messages in failed jobs before clearing them.
4. **Disk Space**: Monitor disk usage and clear jobs when space is low.

---

## Error Handling

Both endpoints return standard HTTP error responses:

**500 Internal Server Error**:
```json
{
  "detail": "Error message here"
}
```

Common errors:
- Database connection issues
- File system permission errors
- Worker thread issues

---

## Implementation Details

### Resume Job Queue

1. Uses `database.reset_processing_jobs_to_queued()` to update job statuses
2. Calls `background_worker.trigger_processing()` to wake up the worker
3. Worker will pick up reset jobs in FIFO order (oldest first)

### Clear Finished Jobs

1. Uses `database.get_finished_jobs()` to get all completed/failed jobs
2. For each job:
   - Removes audio file from `data/uploads/`
   - Removes result zip from `data/results/`
   - Deletes job record from database
3. Logs warnings for files that can't be removed (already deleted, permission issues)
4. Returns total counts of jobs deleted and files removed

---

## Testing

### Test Resume Queue

```bash
# 1. Submit a job
curl -X POST "http://localhost:8000/transcribe/async" \
  -F "audio_file=@test.mp3"

# 2. Check status (should be processing or queued)
curl "http://localhost:8000/jobs/{job_id}/status"

# 3. Restart server (simulates crash)
# Kill and restart the server

# 4. Resume queue
curl -X POST "http://localhost:8000/jobs/resume"

# 5. Check status again (should be queued and will be processed)
curl "http://localhost:8000/jobs/{job_id}/status"
```

### Test Clear Finished Jobs

```bash
# 1. List all jobs
curl "http://localhost:8000/jobs"

# 2. Clear finished jobs
curl -X DELETE "http://localhost:8000/jobs/finished"

# 3. List jobs again (finished jobs should be gone)
curl "http://localhost:8000/jobs"

# 4. Verify files are removed
ls data/uploads/
ls data/results/
```

---

## Version History

- **v2.3.0** (October 2025): Added job management APIs
  - Added `POST /jobs/resume` endpoint
  - Added `DELETE /jobs/finished` endpoint
  - Added database methods for job management

---

**Last Updated**: October 2025
