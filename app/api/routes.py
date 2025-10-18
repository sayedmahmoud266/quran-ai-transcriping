"""
API Routes - FastAPI endpoints for job management.

This module defines all HTTP endpoints for the Quran AI API.
It only handles HTTP concerns - all business logic is in other modules.
"""

import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.queue.job_queue import job_queue
from app.queue.worker import background_worker

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="Quran AI Transcription API",
        description="API for transcribing Quran recitations with verse-level timestamps",
        version="2.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routes
    _register_routes(app)
    
    return app


def _register_routes(app: FastAPI):
    """Register all API routes."""
    
    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "service": "Quran AI Transcription API",
            "version": "2.0.0",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "transcribe_async": "/transcribe/async",
                "job_status": "/jobs/{job_id}/status",
                "job_metadata": "/jobs/{job_id}/metadata",
                "download_result": "/jobs/{job_id}/download",
                "list_jobs": "/jobs",
                "resume_queue": "/jobs/resume",
                "clear_finished": "/jobs/finished"
            }
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "worker_running": background_worker.is_running,
            "worker_processing": background_worker.is_processing,
            "queue_size": job_queue.get_queue_size()
        }
    
    @app.post("/transcribe/async")
    async def transcribe_async(audio_file: UploadFile = File(...)):
        """
        Submit an audio file for asynchronous transcription.
        
        The file is queued for processing and a job ID is returned.
        Use the job ID to check status and retrieve results.
        
        Args:
            audio_file: Audio file (MP3, WAV, M4A, etc.)
            
        Returns:
            Job ID and status URL
        """
        try:
            # Validate file
            if not audio_file.filename:
                raise HTTPException(status_code=400, detail="No filename provided")
            
            # Save uploaded file
            upload_dir = Path(__file__).parent.parent.parent / "data" / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            import uuid
            file_id = str(uuid.uuid4())
            file_ext = Path(audio_file.filename).suffix
            saved_path = upload_dir / f"{file_id}{file_ext}"
            
            # Save file
            with open(saved_path, "wb") as f:
                content = await audio_file.read()
                f.write(content)
            
            logger.info(f"Saved uploaded file: {saved_path}")
            
            # Create job
            job_id = job_queue.create_job(
                audio_file_path=str(saved_path),
                original_filename=audio_file.filename
            )
            
            # Trigger worker
            background_worker.trigger_processing()
            
            return {
                "job_id": job_id,
                "status": "queued",
                "message": "Job created successfully",
                "status_url": f"/jobs/{job_id}/status",
                "download_url": f"/jobs/{job_id}/download"
            }
            
        except Exception as e:
            logger.error(f"Error creating job: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/jobs/{job_id}/status")
    async def get_job_status(job_id: str):
        """
        Get the status of a transcription job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status information
        """
        job = job_queue.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        response = {
            "job_id": job_id,
            "status": job['status'],
            "created_at": job['created_at'],
            "updated_at": job['updated_at'],
            "original_filename": job['original_filename']
        }
        
        # Add error message if failed
        if job.get('error_message'):
            response['error_message'] = job['error_message']
        
        # Add download URL if completed
        if job['status'] == 'completed' and job.get('result_zip_path'):
            response['download_url'] = f"/jobs/{job_id}/download"
            response['metadata_url'] = f"/jobs/{job_id}/metadata"
        
        return response
    
    @app.get("/jobs/{job_id}/metadata")
    async def get_job_metadata(job_id: str):
        """
        Get the metadata of a completed job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job metadata including transcription and verse details
        """
        job = job_queue.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job['status']}"
            )
        
        metadata = job_queue.get_job_metadata(job_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Metadata not found")
        
        return metadata
    
    @app.get("/jobs/{job_id}/download")
    async def download_result(job_id: str):
        """
        Download the result ZIP file of a completed job.
        
        Args:
            job_id: Job ID
            
        Returns:
            ZIP file containing audio segments and metadata
        """
        job = job_queue.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job['status'] != 'completed':
            raise HTTPException(
                status_code=400,
                detail=f"Job is not completed. Current status: {job['status']}"
            )
        
        result_path = job_queue.get_job_result_path(job_id)
        
        if not result_path or not result_path.exists():
            raise HTTPException(status_code=404, detail="Result file not found")
        
        return FileResponse(
            path=str(result_path),
            media_type="application/zip",
            filename=f"transcription_{job_id}.zip"
        )
    
    @app.get("/jobs")
    async def list_jobs(status: Optional[str] = None):
        """
        List all jobs, optionally filtered by status.
        
        Args:
            status: Optional status filter (queued, processing, completed, failed)
            
        Returns:
            List of jobs
        """
        jobs = job_queue.get_all_jobs()
        
        # Filter by status if provided
        if status:
            jobs = [job for job in jobs if job['status'] == status]
        
        return {
            "total": len(jobs),
            "jobs": jobs
        }
    
    @app.post("/jobs/resume")
    async def resume_queue():
        """
        Resume the job queue by resetting processing jobs to queued.
        
        Useful after a server restart or crash.
        
        Returns:
            Success message
        """
        try:
            job_queue.reset_processing_jobs()
            background_worker.trigger_processing()
            
            return {
                "message": "Job queue resumed successfully",
                "queue_size": job_queue.get_queue_size()
            }
        except Exception as e:
            logger.error(f"Error resuming queue: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/jobs/finished")
    async def clear_finished_jobs():
        """
        Delete all finished jobs (completed or failed).
        
        Returns:
            Number of jobs deleted
        """
        try:
            count = job_queue.clear_finished_jobs()
            
            return {
                "message": f"Deleted {count} finished jobs",
                "deleted_count": count
            }
        except Exception as e:
            logger.error(f"Error clearing finished jobs: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/jobs/{job_id}")
    async def delete_job(job_id: str):
        """
        Delete a specific job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Success message
        """
        success = job_queue.delete_job(job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "message": f"Job {job_id} deleted successfully"
        }
