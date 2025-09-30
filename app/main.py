"""
FastAPI application for Quran audio transcription.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
import logging

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.audio_processor import audio_processor
from app.transcription_service import transcription_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        "device": transcription_service.device
    }


@app.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(..., description="Audio file containing Quran recitation")
):
    """
    Transcribe Quran recitation from audio file.
    
    Accepts various audio formats (mp3, wav, m4a, wma, etc.) and returns
    the transcription with verse details and timestamps.
    
    Args:
        audio_file: Uploaded audio file
        
    Returns:
        JSON response with transcription and verse details
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
            return JSONResponse(content=result)
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
        # Clean up temporary file
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
    logger.info("API is ready to accept requests")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Quran AI Transcription API...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
