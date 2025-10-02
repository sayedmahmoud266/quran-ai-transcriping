"""
Database models and operations for background job processing.
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import logging
import json

logger = logging.getLogger(__name__)

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "jobs.db"


class JobStatus:
    """Job status constants."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Database:
    """Database manager for job tracking."""
    
    def __init__(self, db_path: str = None):
        """Initialize database connection."""
        self.db_path = db_path or str(DB_PATH)
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                audio_file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                result_zip_path TEXT,
                metadata_json TEXT,
                transcription_text TEXT
            )
        """)
        
        # Create index on status for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)
        """)
        
        # Create index on created_at for FIFO ordering
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON jobs(created_at)
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    def create_job(self, original_filename: str, audio_file_path: str) -> str:
        """
        Create a new job entry.
        
        Args:
            original_filename: Original name of uploaded file
            audio_file_path: Path where audio file is stored
            
        Returns:
            Job ID (UUID)
        """
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO jobs (
                id, original_filename, audio_file_path, status, created_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (job_id, original_filename, audio_file_path, JobStatus.QUEUED, created_at))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created job {job_id} for file {original_filename}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        Get job details by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job details dictionary or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
        result_zip_path: Optional[str] = None,
        metadata_json: Optional[str] = None,
        transcription_text: Optional[str] = None
    ):
        """
        Update job status and related fields.
        
        Args:
            job_id: Job ID
            status: New status
            error_message: Error message if failed
            result_zip_path: Path to result zip file
            metadata_json: JSON metadata string
            transcription_text: Transcription text
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = ["status = ?"]
        params = [status]
        
        if status == JobStatus.PROCESSING:
            updates.append("started_at = ?")
            params.append(datetime.utcnow().isoformat())
        
        if status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            updates.append("completed_at = ?")
            params.append(datetime.utcnow().isoformat())
        
        if error_message:
            updates.append("error_message = ?")
            params.append(error_message)
        
        if result_zip_path:
            updates.append("result_zip_path = ?")
            params.append(result_zip_path)
        
        if metadata_json:
            updates.append("metadata_json = ?")
            params.append(metadata_json)
        
        if transcription_text:
            updates.append("transcription_text = ?")
            params.append(transcription_text)
        
        params.append(job_id)
        
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated job {job_id} to status {status}")
    
    def get_next_queued_job(self) -> Optional[Dict]:
        """
        Get the next queued job (FIFO).
        
        Returns:
            Job details dictionary or None if no queued jobs
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE status = ? 
            ORDER BY created_at ASC 
            LIMIT 1
        """, (JobStatus.QUEUED,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_all_jobs(self, limit: int = 100) -> List[Dict]:
        """
        Get all jobs, most recent first.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM jobs 
            ORDER BY created_at DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_job(self, job_id: str):
        """
        Delete a job from database.
        
        Args:
            job_id: Job ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Deleted job {job_id}")


# Singleton instance
database = Database()
