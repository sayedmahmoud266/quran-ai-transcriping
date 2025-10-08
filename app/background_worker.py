"""
Background worker for processing audio transcription jobs.
"""

import threading
import time
import logging
from pathlib import Path
import json

from app.database import database, JobStatus
from app.audio_processor import audio_processor
from app.transcription_service import transcription_service
from app.audio_splitter import audio_splitter
from app.debug_utils import DebugRecorder, is_debug_enabled
import app.audio_processor as audio_processor_module
import app.transcription_service as transcription_service_module
import app.audio_splitter as audio_splitter_module

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Background worker for processing transcription jobs."""
    
    def __init__(self):
        """Initialize the background worker."""
        self.is_running = False
        self.is_processing = False
        self.worker_thread = None
        self.lock = threading.Lock()
    
    def start(self):
        """Start the background worker thread."""
        with self.lock:
            if self.is_running:
                logger.warning("Background worker is already running")
                return
            
            self.is_running = True
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            logger.info("Background worker started")
    
    def stop(self):
        """Stop the background worker thread."""
        with self.lock:
            if not self.is_running:
                return
            
            self.is_running = False
            logger.info("Background worker stopped")
    
    def trigger_processing(self):
        """Trigger processing if worker is idle."""
        if not self.is_processing:
            logger.info("Triggering background processing")
            # The worker loop will pick up the job
    
    def _worker_loop(self):
        """Main worker loop that processes jobs."""
        logger.info("Worker loop started")
        
        while self.is_running:
            try:
                # Check for next queued job
                job = database.get_next_queued_job()
                
                if job:
                    self.is_processing = True
                    self._process_job(job)
                    self.is_processing = False
                else:
                    # No jobs, sleep for a bit
                    time.sleep(2)
            
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                self.is_processing = False
                time.sleep(5)
        
        logger.info("Worker loop ended")
    
    def _process_job(self, job: dict):
        """
        Process a single transcription job.
        
        Args:
            job: Job dictionary from database
        """
        job_id = job['id']
        audio_file_path = job['audio_file_path']
        
        logger.info(f"Processing job {job_id}: {job['original_filename']}")
        
        # Initialize debug recorder if enabled
        debug_enabled = is_debug_enabled()
        debug_recorder = DebugRecorder(job_id, enabled=debug_enabled) if debug_enabled else None
        
        if debug_recorder:
            logger.info(f"[{job_id}] Debug mode enabled - data will be saved to .debug/{job_id}")
            # Set debug recorder in all modules
            audio_processor_module.set_debug_recorder(debug_recorder)
            transcription_service_module.set_debug_recorder(debug_recorder)
            audio_splitter_module.set_debug_recorder(debug_recorder)
        
        # Update status to processing
        database.update_job_status(job_id, JobStatus.PROCESSING)
        
        try:
            # Step 1: Process audio
            logger.info(f"[{job_id}] Loading audio file...")
            audio_array, sample_rate = audio_processor.process_audio_file(audio_file_path)
            
            # Step 2: Transcribe
            logger.info(f"[{job_id}] Transcribing audio...")
            result = transcription_service.transcribe_audio(audio_array, sample_rate)
            
            if not result.get('success'):
                raise Exception(result.get('error', 'Transcription failed'))
            
            data = result['data']
            transcription_text = data.get('exact_transcription', '')
            details = data.get('details', [])
            
            # Step 3: Split audio into ayahs
            logger.info(f"[{job_id}] Splitting audio into ayahs...")
            
            if not details:
                raise Exception("No ayah details found in transcription")
            
            zip_buffer, zip_filename = audio_splitter.split_audio_by_ayahs(
                audio_file_path,
                details
            )
            
            # Step 4: Save result zip file
            results_dir = Path(__file__).parent.parent / "data" / "results"
            results_dir.mkdir(parents=True, exist_ok=True)
            
            result_zip_path = results_dir / f"{job_id}.zip"
            with open(result_zip_path, 'wb') as f:
                f.write(zip_buffer.getvalue())
            
            logger.info(f"[{job_id}] Saved result to {result_zip_path}")
            
            # Step 5: Prepare metadata
            metadata = {
                "surah_number": details[0].get('surah_number') if details else None,
                "total_ayahs": len(details),
                "transcription": transcription_text,
                "ayahs": details,
                "diagnostics": data.get('diagnostics', {})
            }
            metadata_json = json.dumps(metadata, ensure_ascii=False)
            
            # Step 6: Update job as completed
            database.update_job_status(
                job_id,
                JobStatus.COMPLETED,
                result_zip_path=str(result_zip_path),
                metadata_json=metadata_json,
                transcription_text=transcription_text
            )
            
            logger.info(f"[{job_id}] Job completed successfully")
            
            # Log debug summary
            if debug_recorder:
                logger.info(debug_recorder.get_summary())
        
        except Exception as e:
            logger.error(f"[{job_id}] Job failed: {e}", exc_info=True)
            database.update_job_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(e)
            )
            
            # Log debug summary even on failure
            if debug_recorder:
                logger.info(debug_recorder.get_summary())
        
        finally:
            # Clear debug recorders
            if debug_recorder:
                audio_processor_module.set_debug_recorder(None)
                transcription_service_module.set_debug_recorder(None)
                audio_splitter_module.set_debug_recorder(None)


# Singleton instance
background_worker = BackgroundWorker()
