"""
Main application entry point - Clean Architecture Version.

This module:
- Initializes the FastAPI application
- Configures logging
- Starts the background worker
- Handles application lifecycle
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log')
    ]
)

logger = logging.getLogger(__name__)

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Import application components
from app.api.routes import create_app
from app.queue.worker import background_worker
from app.queue.job_queue import job_queue

# Create FastAPI app
app = create_app()


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    
    - Starts the background worker
    - Resets any stuck processing jobs
    - Logs startup information
    """
    logger.info("=" * 60)
    logger.info("Quran AI Transcription Service - Starting")
    logger.info("=" * 60)
    
    # Reset processing jobs to queued (in case of crash/restart)
    logger.info("Resetting processing jobs to queued...")
    job_queue.reset_processing_jobs()
    
    # Start background worker
    logger.info("Starting background worker...")
    background_worker.start()
    
    logger.info("Application started successfully")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    
    - Stops the background worker gracefully
    - Logs shutdown information
    """
    logger.info("=" * 60)
    logger.info("Quran AI Transcription Service - Shutting down")
    logger.info("=" * 60)
    
    # Stop background worker
    logger.info("Stopping background worker...")
    background_worker.stop()
    
    logger.info("Application shut down successfully")
    logger.info("=" * 60)


if __name__ == "__main__":
    import uvicorn
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
