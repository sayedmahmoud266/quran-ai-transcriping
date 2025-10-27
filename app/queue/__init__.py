"""
Job Queue Module - Manages background job processing.

This module handles:
- Job creation and queuing
- Job status tracking
- Job execution via background worker
- Job result retrieval
"""

from app.queue.job_queue import JobQueue
from app.queue.worker import BackgroundWorker

__all__ = ['JobQueue', 'BackgroundWorker']
