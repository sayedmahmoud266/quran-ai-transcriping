"""
Debug utilities for saving processing pipeline data at each step.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import numpy as np
import soundfile as sf
from datetime import datetime

logger = logging.getLogger(__name__)

class DebugRecorder:
    """Records processing pipeline data for debugging."""
    
    def __init__(self, job_id: str, enabled: bool = True):
        """
        Initialize debug recorder.
        
        Args:
            job_id: Job identifier
            enabled: Whether debug recording is enabled
        """
        self.job_id = job_id
        self.enabled = enabled
        self.base_dir = None
        self.step_counter = 0  # Track step index for folder naming
        
        if self.enabled:
            # Create debug directory structure
            # Path: project_root/.debug/job_id/
            debug_root = Path(__file__).parent.parent.parent / ".debug"
            self.base_dir = debug_root / job_id
            self.base_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Debug mode enabled for job {job_id} at {self.base_dir}")
    
    def save_step(
        self,
        step_name: str,
        data: Optional[Dict] = None,
        audio_files: Optional[List[Dict]] = None,
        sample_rate: int = 16000
    ):
        """
        Save data for a processing step.
        
        Args:
            step_name: Name of the processing step
            data: Dictionary of data to save as JSON
            audio_files: List of audio file dictionaries with 'name' and 'audio' keys
            sample_rate: Audio sample rate
        """
        if not self.enabled:
            return
        
        try:
            # Create step directory with index prefix
            # Format: {00}_StepName, {01}_StepName, etc.
            indexed_step_name = f"{self.step_counter:02d}_{step_name}"
            step_dir = self.base_dir / indexed_step_name
            step_dir.mkdir(parents=True, exist_ok=True)
            
            # Increment counter for next step
            self.step_counter += 1
            
            # Save timestamp
            timestamp_file = step_dir / "timestamp.txt"
            with open(timestamp_file, 'w') as f:
                f.write(datetime.now().isoformat())
            
            # Save JSON data
            if data is not None:
                json_file = step_dir / "data.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2, default=str)
                logger.debug(f"Saved {step_name} data to {json_file}")
            
            # Save audio files
            if audio_files:
                audio_dir = step_dir / "audio"
                audio_dir.mkdir(exist_ok=True)
                
                for audio_file in audio_files:
                    name = audio_file.get('name', 'unknown')
                    audio = audio_file.get('audio')
                    
                    if audio is not None and len(audio) > 0:
                        # Ensure audio is numpy array
                        if not isinstance(audio, np.ndarray):
                            audio = np.array(audio)
                        
                        # Save as WAV file
                        audio_path = audio_dir / f"{name}.wav"
                        sf.write(str(audio_path), audio, sample_rate)
                        logger.debug(f"Saved {indexed_step_name} audio: {audio_path}")
            
            logger.info(f"Debug: Saved step '{indexed_step_name}' to {step_dir}")
            
        except Exception as e:
            logger.error(f"Error saving debug step '{indexed_step_name}': {e}", exc_info=True)
    
    def save_text(self, step_name: str, filename: str, content: str):
        """
        Save text content to a file.
        
        Args:
            step_name: Name of the processing step (can be indexed like "00_StepName" or just "StepName")
            filename: Name of the file
            content: Text content to save
        """
        if not self.enabled:
            return
        
        try:
            # If step_name doesn't have index prefix, find the matching directory
            if not step_name[0:2].isdigit():
                # Look for existing directory with this step name
                matching_dirs = list(self.base_dir.glob(f"*_{step_name}"))
                if matching_dirs:
                    step_dir = matching_dirs[0]  # Use the first match
                else:
                    # Create new directory with current counter
                    indexed_step_name = f"{self.step_counter:02d}_{step_name}"
                    step_dir = self.base_dir / indexed_step_name
                    self.step_counter += 1
            else:
                # Already indexed
                step_dir = self.base_dir / step_name
            
            step_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = step_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.debug(f"Saved {step_dir.name}/{filename}")
            
        except Exception as e:
            logger.error(f"Error saving text file '{step_name}/{filename}': {e}")
    
    def get_summary(self) -> str:
        """Get summary of saved debug data."""
        if not self.enabled or not self.base_dir:
            return "Debug mode disabled"
        
        summary = [f"Debug data for job {self.job_id}:"]
        summary.append(f"Location: {self.base_dir}")
        summary.append("\nSteps recorded:")
        
        if self.base_dir.exists():
            for step_dir in sorted(self.base_dir.iterdir()):
                if step_dir.is_dir():
                    files = list(step_dir.rglob('*'))
                    summary.append(f"  - {step_dir.name}: {len(files)} files")
        
        return "\n".join(summary)


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled via environment variable."""
    return os.environ.get('DEBUG_MODE', 'false').lower() in ('true', '1', 'yes')
