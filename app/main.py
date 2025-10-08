"""
FastAPI application for Quran audio transcription.
"""

# Load environment variables from .env file FIRST
from dotenv import load_dotenv
load_dotenv()

import os
import tempfile
from pathlib import Path
from typing import Optional
import logging
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.audio_processor import audio_processor
from app.transcription_service import transcription_service
from app.audio_splitter import audio_splitter
from app.database import database, JobStatus
from app.background_worker import background_worker

# Configure logging with both console and file handlers
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Console handler (INFO level)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(detailed_formatter)

# File handler (DEBUG level) - rotates at 10MB, keeps 5 backups
file_handler = RotatingFileHandler(
    log_dir / 'quran_api.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(console_handler)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)
logger.info("Logging configured: Console (INFO) + File (DEBUG) at logs/quran_api.log")

# Create FastAPI app
app = FastAPI(
    title="Quran AI Transcription API",
    description="API for transcribing Quran recitations from audio files",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Quran AI Transcription API",
        "version": "1.0.0",
        "endpoints": {
            "POST /transcribe": "Upload audio file for transcription",
            "GET /health": "Health check endpoint"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": transcription_service.MODEL_NAME,
        "device": transcription_service.device,
        "worker_running": background_worker.is_running,
        "worker_processing": background_worker.is_processing
    }


@app.post("/transcribe/async")
async def transcribe_async(
    audio_file: UploadFile = File(..., description="Audio file containing Quran recitation")
):
    """
    Submit audio file for async transcription processing.
    
    Returns immediately with a job_id that can be used to check status and download results.
    
    Args:
        audio_file: Uploaded audio file
        
    Returns:
        JSON with job_id and status
    """
    try:
        # Validate file
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Get file extension
        file_ext = Path(audio_file.filename).suffix.lower()
        
        # Supported audio formats
        supported_formats = [
            '.mp3', '.wav', '.m4a', '.wma', '.aac', 
            '.flac', '.ogg', '.opus', '.webm'
        ]
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {file_ext}"
            )
        
        logger.info(f"Received async transcription request: {audio_file.filename}")
        
        # Create uploads directory
        uploads_dir = Path(__file__).parent.parent / "data" / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        
        # Save uploaded file with unique name
        import uuid
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        upload_path = uploads_dir / unique_filename
        
        content = await audio_file.read()
        with open(upload_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Saved upload to: {upload_path}")
        
        # Create job in database
        job_id = database.create_job(audio_file.filename, str(upload_path))
        
        # Trigger background processing
        background_worker.trigger_processing()
        
        return {
            "success": True,
            "job_id": job_id,
            "status": JobStatus.QUEUED,
            "message": "Job queued for processing"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating async job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Get the status of a transcription job.
    
    Args:
        job_id: Job ID returned from /transcribe/async
        
    Returns:
        JSON with job status and details
    """
    job = database.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = {
        "job_id": job['id'],
        "status": job['status'],
        "original_filename": job['original_filename'],
        "created_at": job['created_at'],
        "started_at": job['started_at'],
        "completed_at": job['completed_at']
    }
    
    if job['status'] == JobStatus.FAILED:
        response['error'] = job['error_message']
    
    if job['status'] == JobStatus.COMPLETED:
        response['download_url'] = f"/jobs/{job_id}/download"
        response['metadata_url'] = f"/jobs/{job_id}/metadata"
    
    return response


@app.get("/jobs/{job_id}/download")
async def download_result(job_id: str):
    """
    Download the result zip file for a completed job.
    
    Args:
        job_id: Job ID
        
    Returns:
        Zip file with ayah segments
    """
    job = database.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['status'] != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job['status']}"
        )
    
    result_path = Path(job['result_zip_path'])
    
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        path=result_path,
        media_type="application/zip",
        filename=f"{job['original_filename']}_ayahs.zip"
    )


@app.get("/jobs/{job_id}/metadata")
async def get_metadata(job_id: str):
    """
    Get the metadata JSON for a completed job.
    
    Args:
        job_id: Job ID
        
    Returns:
        JSON with transcription and ayah metadata
    """
    job = database.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['status'] != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed yet. Current status: {job['status']}"
        )
    
    if not job['metadata_json']:
        raise HTTPException(status_code=404, detail="Metadata not found")
    
    import json
    metadata = json.loads(job['metadata_json'])
    
    return metadata


@app.get("/jobs")
async def list_jobs(limit: int = 100):
    """
    List all jobs (most recent first) with detailed information.
    
    Args:
        limit: Maximum number of jobs to return
        
    Returns:
        List of jobs with detailed info including URLs for completed jobs
    """
    jobs = database.get_all_jobs(limit)
    
    job_list = []
    for job in jobs:
        job_info = {
            "job_id": job['id'],
            "original_filename": job['original_filename'],
            "status": job['status'],
            "created_at": job['created_at'],
            "started_at": job['started_at'],
            "completed_at": job['completed_at']
        }
        
        # Add error message for failed jobs
        if job['status'] == JobStatus.FAILED and job.get('error_message'):
            job_info['error_message'] = job['error_message']
        
        # Add URLs for completed jobs
        if job['status'] == JobStatus.COMPLETED:
            job_info['download_url'] = f"/jobs/{job['id']}/download"
            job_info['metadata_url'] = f"/jobs/{job['id']}/metadata"
        
        # Add status URL for all jobs
        job_info['status_url'] = f"/jobs/{job['id']}/status"
        
        job_list.append(job_info)
    
    return {
        "total": len(jobs),
        "jobs": job_list
    }


@app.post("/jobs/resume")
async def resume_job_queue():
    """
    Resume the job queue by restarting any jobs that are still in processing status.
    
    This is useful when the server was restarted while jobs were being processed.
    Those jobs will be reset to queued status and will be picked up by the worker again.
    
    Returns:
        JSON with number of jobs reset and triggered processing status
    """
    try:
        # Reset any processing jobs back to queued
        reset_count = database.reset_processing_jobs_to_queued()
        
        # Trigger the background worker to start processing
        background_worker.trigger_processing()
        
        logger.info(f"Resume queue: reset {reset_count} jobs, triggered processing")
        
        return {
            "success": True,
            "message": f"Job queue resumed. {reset_count} processing job(s) reset to queued.",
            "jobs_reset": reset_count,
            "worker_running": background_worker.is_running,
            "worker_processing": background_worker.is_processing
        }
    
    except Exception as e:
        logger.error(f"Error resuming job queue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/jobs/finished")
async def clear_finished_jobs():
    """
    Clear all finished jobs (completed or failed) from the database and remove their files.
    
    This will:
    1. Delete all completed and failed jobs from the database
    2. Remove their uploaded audio files from data/uploads/
    3. Remove their result zip files from data/results/
    
    Returns:
        JSON with number of jobs deleted and files removed
    """
    try:
        import os
        
        # Get all finished jobs
        finished_jobs = database.get_finished_jobs()
        
        if not finished_jobs:
            return {
                "success": True,
                "message": "No finished jobs to clear",
                "jobs_deleted": 0,
                "files_removed": 0
            }
        
        files_removed = 0
        
        # Delete files and database entries for each job
        for job in finished_jobs:
            job_id = job['id']
            
            # Remove uploaded audio file
            audio_file_path = job.get('audio_file_path')
            if audio_file_path and os.path.exists(audio_file_path):
                try:
                    os.remove(audio_file_path)
                    files_removed += 1
                    logger.info(f"Removed audio file: {audio_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove audio file {audio_file_path}: {e}")
            
            # Remove result zip file
            result_zip_path = job.get('result_zip_path')
            if result_zip_path and os.path.exists(result_zip_path):
                try:
                    os.remove(result_zip_path)
                    files_removed += 1
                    logger.info(f"Removed result file: {result_zip_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove result file {result_zip_path}: {e}")
            
            # Delete job from database
            database.delete_job(job_id)
        
        jobs_deleted = len(finished_jobs)
        
        logger.info(f"Cleared {jobs_deleted} finished jobs and removed {files_removed} files")
        
        return {
            "success": True,
            "message": f"Cleared {jobs_deleted} finished job(s) and removed {files_removed} file(s)",
            "jobs_deleted": jobs_deleted,
            "files_removed": files_removed
        }
    
    except Exception as e:
        logger.error(f"Error clearing finished jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file containing Quran recitation"),
    split_audio: bool = Form(False, description="Split audio into individual ayah files and return as zip")
):
    """
    Transcribe Quran recitation from audio file.
    
    Accepts various audio formats (mp3, wav, m4a, wma, etc.) and returns
    the transcription with verse details and timestamps.
    
    Args:
        audio_file: Uploaded audio file
        split_audio: If True, returns a zip file with individual ayah audio segments
        
    Returns:
        JSON response with transcription and verse details, or
        Zip file with individual ayah segments if split_audio=True
    """
    temp_file_path = None
    
    try:
        # Validate file
        if not audio_file:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Get file extension
        file_ext = Path(audio_file.filename).suffix.lower()
        
        # Supported audio formats
        supported_formats = [
            '.mp3', '.wav', '.m4a', '.wma', '.aac', 
            '.flac', '.ogg', '.opus', '.webm'
        ]
        
        if file_ext not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format: {file_ext}. Supported formats: {', '.join(supported_formats)}"
            )
        
        logger.info(f"Processing audio file: {audio_file.filename}")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file_path = temp_file.name
            content = await audio_file.read()
            temp_file.write(content)
        
        logger.info(f"Audio file saved to: {temp_file_path}")
        
        # Process audio file
        try:
            audio_array, sample_rate = audio_processor.process_audio_file(temp_file_path)
            logger.info(f"Audio processed: sample_rate={sample_rate}, duration={len(audio_array)/sample_rate:.2f}s")
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Error processing audio file: {str(e)}"
            )
        
        # Transcribe audio
        try:
            result = transcription_service.transcribe_audio(audio_array, sample_rate)
            logger.info("Transcription completed successfully")
            
            # If split_audio is True, split the audio and return zip file
            if split_audio:
                logger.info("Splitting audio into individual ayah segments...")
                
                # Check if we have ayah details
                if not result.get('success') or not result.get('data', {}).get('details'):
                    raise HTTPException(
                        status_code=400,
                        detail="No ayah details found in transcription. Cannot split audio."
                    )
                
                ayah_details = result['data']['details']
                
                try:
                    # Get word timestamps from result if available
                    word_timestamps = result.get('data', {}).get('word_timestamps', None)
                    
                    # Split audio and create zip
                    zip_buffer, zip_filename = audio_splitter.split_audio_by_ayahs(
                        temp_file_path,
                        ayah_details,
                        word_timestamps
                    )
                    
                    logger.info(f"Audio split successfully: {len(ayah_details)} ayahs")
                    
                    # Clean up temp file now that we're done with it
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                            logger.info(f"Temporary file removed: {temp_file_path}")
                        except Exception as e:
                            logger.warning(f"Failed to remove temporary file: {e}")
                    
                    # Return zip file as streaming response
                    return StreamingResponse(
                        zip_buffer,
                        media_type="application/zip",
                        headers={
                            "Content-Disposition": f"attachment; filename={zip_filename}"
                        }
                    )
                    
                except Exception as e:
                    logger.error(f"Error splitting audio: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error splitting audio: {str(e)}"
                    )
            
            # Return JSON response if split_audio is False
            return JSONResponse(content=result)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Error during transcription: {str(e)}"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
    
    finally:
        # Clean up temporary file (if not already cleaned up in split_audio branch)
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary file removed: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Quran AI Transcription API...")
    logger.info(f"Model: {transcription_service.MODEL_NAME}")
    logger.info(f"Device: {transcription_service.device}")
    
    # Log debug mode status
    from app.debug_utils import is_debug_enabled
    if is_debug_enabled():
        logger.info("🐛 DEBUG MODE ENABLED - Pipeline data will be saved to .debug/ folder")
    else:
        logger.info("Debug mode disabled (set DEBUG_MODE=true in .env to enable)")
    
    # Start background worker
    background_worker.start()
    logger.info("Background worker started")
    
    logger.info("API is ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Quran AI Transcription API...")
    
    # Stop background worker
    background_worker.stop()
    logger.info("Background worker stopped")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
