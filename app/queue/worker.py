"""
Background Worker - Processes jobs from the queue using the pipeline.

This module is responsible for:
- Running background worker thread
- Processing jobs from the queue
- Executing the transcription pipeline
- Handling job results and errors
"""

import threading
import time
import logging
from pathlib import Path
import json

from app.queue.job_queue import job_queue
from app.database import JobStatus
from app.utils.audio_loader import load_audio_file
from app.utils.audio_splitter import split_audio_by_ayahs
from app.utils.debug_utils import DebugRecorder, is_debug_enabled
from app.pipeline.orchestrator import PipelineOrchestrator

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """
    Background worker for processing transcription jobs.
    
    This worker:
    - Runs in a separate thread
    - Polls the job queue for new jobs
    - Executes the transcription pipeline
    - Saves results and updates job status
    """
    
    def __init__(self):
        """Initialize the background worker."""
        self.is_running = False
        self.is_processing = False
        self.worker_thread = None
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the background worker thread."""
        with self.lock:
            if self.is_running:
                self.logger.warning("Background worker is already running")
                return
            
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            self.logger.info("Background worker started")
    
    def stop(self):
        """Stop the background worker thread."""
        with self.lock:
            if not self.is_running:
                return
            
            self.is_running = False
            self.logger.info("Background worker stopped")
    
    def trigger_processing(self):
        """Trigger processing if worker is idle."""
        if not self.is_processing:
            self.logger.info("Triggering background processing")
    
    def _worker_loop(self):
        """Main worker loop that processes jobs."""
        self.logger.info("Worker loop started")
        
        while self.is_running:
            try:
                # Check for next queued job
                job = job_queue.get_next_queued_job()
                
                if job:
                    self.is_processing = True
                    self._process_job(job)
                    self.is_processing = False
                else:
                    # No jobs, sleep for a bit
                    time.sleep(2)
            
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}", exc_info=True)
                self.is_processing = False
                time.sleep(5)
        
        self.logger.info("Worker loop ended")
    
    def _process_job(self, job: dict):
        """
        Process a single transcription job using the pipeline.
        
        Args:
            job: Job dictionary from queue
        """
        job_id = job['id']
        audio_file_path = job['audio_file_path']
        
        self.logger.info(f"Processing job {job_id}: {job['original_filename']}")
        
        # Initialize debug recorder if enabled
        debug_enabled = is_debug_enabled()
        debug_recorder = DebugRecorder(job_id, enabled=debug_enabled) if debug_enabled else None
        
        if debug_recorder:
            self.logger.info(f"[{job_id}] Debug mode enabled - data will be saved to .debug/{job_id}")
        
        # Update status to processing
        job_queue.update_job_status(job_id, JobStatus.PROCESSING)
        
        try:
            # Step 1: Load audio file
            self.logger.info(f"[{job_id}] Loading audio file...")
            audio_array, sample_rate = load_audio_file(audio_file_path)
            
            # Step 2: Create and execute pipeline
            self.logger.info(f"[{job_id}] Creating transcription pipeline...")
            
            # Import dependencies
            from app.inference.transcription import transcription_service
            
            # Create pipeline
            pipeline = PipelineOrchestrator.create_full_pipeline(
                model=transcription_service.model,
                processor=transcription_service.processor,
                device=transcription_service.device,
                config={}
            )
            
            # Execute pipeline
            self.logger.info(f"[{job_id}] Executing pipeline...")
            context = PipelineOrchestrator.execute_pipeline(
                pipeline=pipeline,
                audio_array=audio_array,
                sample_rate=sample_rate,
                debug_recorder=debug_recorder
            )
            
            # Get results
            transcription_text = context.final_transcription
            verse_details = context.verse_details
            
            if not verse_details:
                raise Exception("No verse details found in transcription")
            
            # Step 3: Split audio into ayahs
            self.logger.info(f"[{job_id}] Splitting audio into ayahs...")
            
            zip_buffer, zip_filename = split_audio_by_ayahs(
                audio_file_path,
                verse_details
            )
            
            # Step 4: Save result zip file
            results_dir = Path(__file__).parent.parent.parent / "data" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            result_zip_path = results_dir / f"{job_id}.zip"
            with open(result_zip_path, 'wb') as f:
                f.write(zip_buffer.getvalue())
            
            self.logger.info(f"[{job_id}] Saved result to {result_zip_path}")
            
            # Step 5: Prepare metadata
            pipeline_summary = PipelineOrchestrator.get_pipeline_summary(context)
            
            metadata = {
                "surah_number": verse_details[0].get('surah_number') if verse_details else None,
                "total_ayahs": len(verse_details),
                "transcription": transcription_text,
                "ayahs": verse_details,
                "pipeline_summary": pipeline_summary,
                "diagnostics": {
                    "audio_duration": context.get('audio_duration', 0),
                    "total_chunks": len(context.chunks),
                    "total_verses": len(verse_details)
                }
            }
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            # Step 6: Update job as completed
            job_queue.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                result_zip_path=str(result_zip_path),
                metadata_json=metadata_json,
                transcription_text=transcription_text
            )
            
            self.logger.info(f"[{job_id}] Job completed successfully")
            
            # Log debug summary
            if debug_recorder:
                self.logger.info(debug_recorder.get_summary())
        
        except Exception as e:
            self.logger.error(f"[{job_id}] Job failed: {e}", exc_info=True)
            job_queue.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
            
            # Log debug summary even on failure
            if debug_recorder:
                self.logger.info(debug_recorder.get_summary())


# Singleton instance
background_worker = BackgroundWorker()
