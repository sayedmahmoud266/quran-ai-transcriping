"""
Job Queue - Manages job lifecycle and queue operations.

This module is responsible for:
- Creating new jobs
- Queuing jobs for processing
- Tracking job status
- Retrieving job results
- Managing job lifecycle
"""

import logging
from typing import Optional, List, Dict
from pathlib import Path

from app.database import database, JobStatus

logger = logging.getLogger(__name__)


class JobQueue:
    """
    Job Queue manager for transcription jobs.
    
    This class provides a clean interface for job management,
    separating queue operations from API and worker concerns.
    """
    
    def __init__(self):
        """Initialize the job queue."""
        self.logger = logging.getLogger(__name__)
        self.db = database
    
    def _map_job_fields(self, job: Dict) -> Dict:
        """
        Map database fields to API fields.
        
        Args:
            job: Job dictionary from database
            
        Returns:
            Job dictionary with mapped fields
        """
        if job and 'id' in job:
            job['job_id'] = job.pop('id')
        return job
    
    def create_job(self, audio_file_path: str, original_filename: str) -> str:
        """
        Create a new transcription job.
        
        Args:
            audio_file_path: Path to the uploaded audio file
            original_filename: Original name of the uploaded file
            
        Returns:
            Job ID (UUID string)
        """
        # Note: database.create_job expects (original_filename, audio_file_path)
        job_id = database.create_job(original_filename, audio_file_path)
        self.logger.info(f"Created job {job_id}: {original_filename}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        Get job details by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job dictionary or None if not found
        """
        job = database.get_job(job_id)
        return self._map_job_fields(job) if job else None
    
    def get_job_status(self, job_id: str) -> Optional[str]:
        """
        Get job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status string or None if not found
        """
        job = database.get_job(job_id)
        return job['status'] if job else None
    
    def get_all_jobs(self) -> List[Dict]:
        """
        Get all jobs.
        
        Returns:
            List of job dictionaries
        """
        jobs = database.get_all_jobs()
        return [self._map_job_fields(job) for job in jobs]
    
    def get_next_queued_job(self) -> Optional[Dict]:
        """
        Get the next job in the queue.
        
        Returns:
            Job dictionary or None if queue is empty
        """
        return database.get_next_queued_job()
    
    def update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        result_zip_path: Optional[str] = None,
        metadata_json: Optional[str] = None,
        transcription_text: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update job status and results.
        
        Args:
            job_id: Job ID
            status: New job status
            result_zip_path: Path to result ZIP file (optional)
            metadata_json: JSON metadata (optional)
            transcription_text: Transcription text (optional)
            error_message: Error message if failed (optional)
        """
        database.update_job_status(
            job_id=job_id,
            status=status,
            result_zip_path=result_zip_path,
            metadata_json=metadata_json,
            transcription_text=transcription_text,
            error_message=error_message
        )
        # Handle both enum and string status
        status_str = status.value if hasattr(status, 'value') else status
        self.logger.info(f"Updated job {job_id} status to {status_str}")
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if deleted, False if not found
        """
        success = database.delete_job(job_id)
        if success:
            self.logger.info(f"Deleted job {job_id}")
        return success
    
    def get_finished_jobs(self) -> List[Dict]:
        """
        Get all finished jobs (completed or failed).
        
        Returns:
            List of finished job dictionaries
        """
        return database.get_finished_jobs()
    
    def clear_finished_jobs(self) -> int:
        """
        Delete all finished jobs.
        
        Returns:
            Number of jobs deleted
        """
        jobs = self.get_finished_jobs()
        count = 0
        for job in jobs:
            if self.delete_job(job['id']):
                count += 1
        
        self.logger.info(f"Cleared {count} finished jobs")
        return count
    
    def reset_processing_jobs(self) -> None:
        """
        Reset all processing jobs to queued status.
        
        Useful for recovering from crashes or restarts.
        """
        database.reset_processing_jobs_to_queued()
        self.logger.info("Reset processing jobs to queued")
    
    def get_job_result_path(self, job_id: str) -> Optional[Path]:
        """
        Get the path to the job result ZIP file.
        
        Args:
            job_id: Job ID
            
        Returns:
            Path to ZIP file or None if not available
        """
        job = self.get_job(job_id)
        if not job or not job.get('result_zip_path'):
            return None
        
        result_path = Path(job['result_zip_path'])
        if result_path.exists():
            return result_path
        
        return None
    
    def get_job_metadata(self, job_id: str) -> Optional[Dict]:
        """
        Get job metadata (parsed from JSON).
        
        Args:
            job_id: Job ID
            
        Returns:
            Metadata dictionary or None if not available
        """
        import json
        
        job = self.get_job(job_id)
        if not job or not job.get('metadata_json'):
            return None
        
        try:
            return json.loads(job['metadata_json'])
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse metadata for job {job_id}")
            return None
    
    def is_job_complete(self, job_id: str) -> bool:
        """
        Check if job is complete.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job is completed, False otherwise
        """
        status = self.get_job_status(job_id)
        return status == JobStatus.COMPLETED.value if status else False
    
    def is_job_failed(self, job_id: str) -> bool:
        """
        Check if job failed.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job failed, False otherwise
        """
        status = self.get_job_status(job_id)
        return status == JobStatus.FAILED.value if status else False
    
    def is_job_processing(self, job_id: str) -> bool:
        """
        Check if job is currently processing.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job is processing, False otherwise
        """
        status = self.get_job_status(job_id)
        return status == JobStatus.PROCESSING.value if status else False
    
    def get_queue_size(self) -> int:
        """
        Get the number of jobs in the queue.
        
        Returns:
            Number of queued jobs
        """
        jobs = self.get_all_jobs()
        return sum(1 for job in jobs if job['status'] == 'queued')


# Singleton instance
job_queue = JobQueue()
