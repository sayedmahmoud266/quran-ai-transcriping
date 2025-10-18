"""
Base classes for the pipeline architecture.

This module defines the core abstractions for building a modular, extensible pipeline.
Uses the Chain of Responsibility and Pipeline design patterns.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class PipelineStepStatus(Enum):
    """Status of a pipeline step execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineContext:
    """
    Context object that flows through the pipeline.
    
    This is the main data structure that gets passed between pipeline steps.
    Each step can read from and write to this context.
    
    Attributes:
        audio_array: Raw audio data as numpy array
        sample_rate: Audio sample rate
        chunks: List of audio chunks with metadata
        transcriptions: List of transcription results
        matched_verses: List of matched Quran verses
        metadata: Additional metadata dictionary
        debug_data: Debug information for each step
    """
    # Input data
    audio_array: Optional[Any] = None
    sample_rate: int = 16000
    
    # Processing data
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    transcriptions: List[Dict[str, Any]] = field(default_factory=list)
    matched_verses: List[Dict[str, Any]] = field(default_factory=list)
    
    # Output data
    final_transcription: str = ""
    verse_details: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    debug_data: Dict[str, Any] = field(default_factory=dict)
    
    # Execution tracking
    step_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from metadata."""
        return self.metadata.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in metadata."""
        self.metadata[key] = value
    
    def add_debug_info(self, step_name: str, data: Dict[str, Any]) -> None:
        """Add debug information for a step."""
        self.debug_data[step_name] = data
    
    def add_step_result(self, step_name: str, status: PipelineStepStatus, 
                       duration: float, data: Optional[Dict[str, Any]] = None) -> None:
        """Record the result of a step execution."""
        self.step_results[step_name] = {
            'status': status.value,
            'duration': duration,
            'data': data or {}
        }


class PipelineStep(ABC):
    """
    Abstract base class for all pipeline steps.
    
    Each step must implement the process() method which takes a PipelineContext
    and returns a modified PipelineContext.
    
    Steps should be:
    - Independent: Not rely on specific implementation details of other steps
    - Idempotent: Produce the same result given the same input
    - Focused: Do one thing well
    - Testable: Easy to unit test in isolation
    """
    
    def __init__(self, name: Optional[str] = None):
        """
        Initialize the pipeline step.
        
        Args:
            name: Optional custom name for the step. If not provided,
                  uses the class name.
        """
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
    
    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """
        Process the pipeline context.
        
        This is the main method that must be implemented by each step.
        It should:
        1. Read necessary data from the context
        2. Perform its specific processing
        3. Write results back to the context
        4. Return the modified context
        
        Args:
            context: The pipeline context containing all data
            
        Returns:
            Modified pipeline context
            
        Raises:
            Exception: If processing fails
        """
        pass
    
    def validate_input(self, context: PipelineContext) -> bool:
        """
        Validate that the context has all required inputs for this step.
        
        Override this method to add custom validation logic.
        
        Args:
            context: The pipeline context
            
        Returns:
            True if validation passes, False otherwise
        """
        return True
    
    def should_skip(self, context: PipelineContext) -> bool:
        """
        Determine if this step should be skipped.
        
        Override this method to add conditional execution logic.
        
        Args:
            context: The pipeline context
            
        Returns:
            True if step should be skipped, False otherwise
        """
        return False
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the step with validation and error handling.
        
        This method wraps the process() method with:
        - Input validation
        - Skip logic
        - Timing
        - Error handling
        - Result recording
        
        Args:
            context: The pipeline context
            
        Returns:
            Modified pipeline context
        """
        start_time = time.time()
        
        try:
            # Check if step should be skipped
            if self.should_skip(context):
                self.logger.info(f"Skipping step: {self.name}")
                context.add_step_result(
                    self.name,
                    PipelineStepStatus.SKIPPED,
                    time.time() - start_time
                )
                return context
            
            # Validate input
            if not self.validate_input(context):
                raise ValueError(f"Input validation failed for step: {self.name}")
            
            self.logger.info(f"Executing step: {self.name}")
            
            # Process the context
            context = self.process(context)
            
            # Record success
            duration = time.time() - start_time
            context.add_step_result(
                self.name,
                PipelineStepStatus.COMPLETED,
                duration
            )
            
            self.logger.info(f"Completed step: {self.name} in {duration:.2f}s")
            
            return context
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Step {self.name} failed: {e}", exc_info=True)
            
            context.add_step_result(
                self.name,
                PipelineStepStatus.FAILED,
                duration,
                {'error': str(e)}
            )
            
            raise
    
    def __repr__(self) -> str:
        """String representation of the step."""
        return f"{self.__class__.__name__}(name='{self.name}')"


class Pipeline:
    """
    Pipeline orchestrator that executes a sequence of steps.
    
    The pipeline:
    - Maintains a list of steps to execute
    - Executes steps in order
    - Handles errors and rollback
    - Provides hooks for monitoring and debugging
    """
    
    def __init__(self, name: str = "Pipeline", steps: Optional[List[PipelineStep]] = None):
        """
        Initialize the pipeline.
        
        Args:
            name: Name of the pipeline
            steps: Initial list of steps (can be empty)
        """
        self.name = name
        self.steps: List[PipelineStep] = steps or []
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    def add_step(self, step: PipelineStep) -> 'Pipeline':
        """
        Add a step to the pipeline.
        
        Args:
            step: The step to add
            
        Returns:
            Self for method chaining
        """
        self.steps.append(step)
        self.logger.debug(f"Added step: {step.name}")
        return self
    
    def add_steps(self, steps: List[PipelineStep]) -> 'Pipeline':
        """
        Add multiple steps to the pipeline.
        
        Args:
            steps: List of steps to add
            
        Returns:
            Self for method chaining
        """
        for step in steps:
            self.add_step(step)
        return self
    
    def remove_step(self, step_name: str) -> 'Pipeline':
        """
        Remove a step from the pipeline by name.
        
        Args:
            step_name: Name of the step to remove
            
        Returns:
            Self for method chaining
        """
        self.steps = [s for s in self.steps if s.name != step_name]
        self.logger.debug(f"Removed step: {step_name}")
        return self
    
    def insert_step(self, index: int, step: PipelineStep) -> 'Pipeline':
        """
        Insert a step at a specific position.
        
        Args:
            index: Position to insert at
            step: The step to insert
            
        Returns:
            Self for method chaining
        """
        self.steps.insert(index, step)
        self.logger.debug(f"Inserted step: {step.name} at position {index}")
        return self
    
    def get_step(self, step_name: str) -> Optional[PipelineStep]:
        """
        Get a step by name.
        
        Args:
            step_name: Name of the step
            
        Returns:
            The step if found, None otherwise
        """
        for step in self.steps:
            if step.name == step_name:
                return step
        return None
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute all steps in the pipeline.
        
        Args:
            context: Initial pipeline context
            
        Returns:
            Final pipeline context after all steps
            
        Raises:
            Exception: If any step fails
        """
        self.logger.info(f"Starting pipeline: {self.name} with {len(self.steps)} steps")
        start_time = time.time()
        
        try:
            for i, step in enumerate(self.steps, 1):
                self.logger.info(f"Step {i}/{len(self.steps)}: {step.name}")
                context = step.execute(context)
            
            duration = time.time() - start_time
            self.logger.info(f"Pipeline {self.name} completed successfully in {duration:.2f}s")
            
            return context
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Pipeline {self.name} failed after {duration:.2f}s: {e}")
            raise
    
    def execute_from(self, context: PipelineContext, start_step: str) -> PipelineContext:
        """
        Execute pipeline starting from a specific step.
        
        Useful for resuming or debugging.
        
        Args:
            context: Pipeline context
            start_step: Name of the step to start from
            
        Returns:
            Final pipeline context
        """
        start_index = None
        for i, step in enumerate(self.steps):
            if step.name == start_step:
                start_index = i
                break
        
        if start_index is None:
            raise ValueError(f"Step '{start_step}' not found in pipeline")
        
        self.logger.info(f"Starting pipeline from step: {start_step}")
        
        for step in self.steps[start_index:]:
            context = step.execute(context)
        
        return context
    
    def execute_until(self, context: PipelineContext, end_step: str) -> PipelineContext:
        """
        Execute pipeline until a specific step (inclusive).
        
        Useful for partial execution or debugging.
        
        Args:
            context: Pipeline context
            end_step: Name of the step to stop at (inclusive)
            
        Returns:
            Pipeline context after executing up to end_step
        """
        for step in self.steps:
            context = step.execute(context)
            if step.name == end_step:
                self.logger.info(f"Stopping pipeline at step: {end_step}")
                break
        
        return context
    
    def get_step_names(self) -> List[str]:
        """Get list of all step names in order."""
        return [step.name for step in self.steps]
    
    def __repr__(self) -> str:
        """String representation of the pipeline."""
        return f"Pipeline(name='{self.name}', steps={len(self.steps)})"
