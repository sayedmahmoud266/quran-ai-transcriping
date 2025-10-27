```markdown
# Pipeline Architecture Documentation

**Version:** 2.0  
**Date:** 2025-10-18  
**Status:** Production Ready

## Overview

The Quran AI transcription system now uses a **modular pipeline architecture** based on the **Chain of Responsibility** and **Pipeline** design patterns. This architecture provides:

- ✅ **Modularity**: Each step is independent and self-contained
- ✅ **Flexibility**: Easy to add, remove, or reorder steps
- ✅ **Testability**: Each step can be tested in isolation
- ✅ **Maintainability**: Clear separation of concerns
- ✅ **Reusability**: Steps can be reused in different pipelines
- ✅ **Debuggability**: Built-in execution tracking and logging

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Pipeline Orchestrator                    │
│                  (Factory & Configuration)                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Pipeline Engine                         │
│                  (Execution & Monitoring)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  PipelineContext     │◄─────────────┐
              │  (Shared Data)       │              │
              └──────────┬───────────┘              │
                         │                          │
                         ▼                          │
        ┌────────────────────────────────┐          │
        │      Pipeline Steps            │          │
        │  (Chain of Responsibility)     │          │
        └────────────────────────────────┘          │
                         │                          │
         ┌───────────────┼───────────────┐          │
         │               │               │          │
         ▼               ▼               ▼          │
    ┌────────┐     ┌────────┐     ┌────────┐       │
    │ Step 1 │────▶│ Step 2 │────▶│ Step 3 │───────┘
    └────────┘     └────────┘     └────────┘
   Resampling    Silence Det.   Chunk Merge
```

## Core Components

### 1. PipelineContext

The **PipelineContext** is the data container that flows through the pipeline. It holds:

```python
@dataclass
class PipelineContext:
    # Input data
    audio_array: np.ndarray
    sample_rate: int
    
    # Processing data
    chunks: List[Dict]
    transcriptions: List[Dict]
    matched_verses: List[Dict]
    
    # Output data
    final_transcription: str
    verse_details: List[Dict]
    
    # Metadata & tracking
    metadata: Dict
    debug_data: Dict
    step_results: Dict
```

**Key Methods:**
- `get(key, default)` - Get metadata value
- `set(key, value)` - Set metadata value
- `add_debug_info(step_name, data)` - Add debug information
- `add_step_result(step_name, status, duration, data)` - Record step execution

### 2. PipelineStep (Abstract Base Class)

All pipeline steps inherit from **PipelineStep**:

```python
class PipelineStep(ABC):
    @abstractmethod
    def process(self, context: PipelineContext) -> PipelineContext:
        """Main processing logic - must be implemented"""
        pass
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate inputs before processing"""
        return True
    
    def should_skip(self, context: PipelineContext) -> bool:
        """Determine if step should be skipped"""
        return False
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute with validation, timing, and error handling"""
        # Wraps process() with infrastructure code
        pass
```

**Step Lifecycle:**
1. `should_skip()` - Check if step should run
2. `validate_input()` - Validate required inputs
3. `process()` - Execute main logic
4. Record results and timing
5. Return modified context

### 3. Pipeline

The **Pipeline** class orchestrates step execution:

```python
class Pipeline:
    def __init__(self, name: str, steps: List[PipelineStep] = None):
        self.name = name
        self.steps = steps or []
    
    def add_step(self, step: PipelineStep) -> 'Pipeline':
        """Add a step (chainable)"""
        
    def remove_step(self, step_name: str) -> 'Pipeline':
        """Remove a step by name"""
        
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute all steps in order"""
        
    def execute_from(self, context: PipelineContext, start_step: str):
        """Execute from a specific step"""
        
    def execute_until(self, context: PipelineContext, end_step: str):
        """Execute until a specific step"""
```

### 4. PipelineOrchestrator

The **PipelineOrchestrator** provides factory methods:

```python
class PipelineOrchestrator:
    @staticmethod
    def create_full_pipeline(model, processor, device, quran_data, config):
        """Create complete pipeline with all 10 steps"""
        
    @staticmethod
    def create_partial_pipeline(step_names, ...):
        """Create pipeline with only specified steps"""
        
    @staticmethod
    def execute_pipeline(pipeline, audio_array, sample_rate, debug_recorder):
        """Execute pipeline with audio data"""
        
    @staticmethod
    def get_pipeline_summary(context):
        """Get execution summary"""
```

## Pipeline Steps

### Step 1: AudioResamplingStep
- **Input**: `audio_array`, `sample_rate`
- **Output**: Resampled `audio_array` at 16kHz
- **Purpose**: Prepare audio for Whisper model

### Step 2: SilenceDetectionStep
- **Input**: `audio_array`, `sample_rate`
- **Output**: `chunks` (list of audio segments)
- **Purpose**: Split audio by silence detection

### Step 3: ChunkMergingStep
- **Input**: `chunks`
- **Output**: Merged `chunks`
- **Purpose**: Merge short chunks or chunks with small gaps

### Step 4: ChunkTranscriptionStep
- **Input**: `chunks`, Whisper model
- **Output**: `transcriptions` (list of text results)
- **Purpose**: Transcribe each chunk using Whisper

### Step 5: DuplicateRemovalStep
- **Input**: `transcriptions`
- **Output**: Deduplicated `transcriptions`
- **Purpose**: Remove duplicate words at chunk boundaries

### Step 6: TranscriptionCombiningStep
- **Input**: `transcriptions`
- **Output**: `final_transcription` (combined text)
- **Purpose**: Combine all transcriptions into one text

### Step 7: VerseMatchingStep
- **Input**: `final_transcription`, QuranData
- **Output**: `matched_verses`
- **Purpose**: Match transcription to Quran verses

### Step 8: TimestampCalculationStep
- **Input**: `matched_verses`, `chunks`
- **Output**: `verse_details` with timestamps
- **Purpose**: Calculate accurate timestamps for verses

### Step 9: SilenceSplittingStep
- **Input**: `verse_details`
- **Output**: Adjusted `verse_details`
- **Purpose**: Split silence between consecutive verses

### Step 10: AudioSplittingStep
- **Input**: `verse_details`
- **Output**: Metadata flag for splitting readiness
- **Purpose**: Prepare data for audio file splitting

## Usage Examples

### Basic Usage

```python
from app.pipeline.orchestrator import PipelineOrchestrator
from app.transcription_service import transcription_service
from app.quran_data import quran_data

# Create pipeline
pipeline = PipelineOrchestrator.create_full_pipeline(
    model=transcription_service.model,
    processor=transcription_service.processor,
    device=transcription_service.device,
    quran_data=quran_data,
    config={}
)

# Execute pipeline
context = PipelineOrchestrator.execute_pipeline(
    pipeline=pipeline,
    audio_array=audio_data,
    sample_rate=16000
)

# Get results
transcription = context.final_transcription
verses = context.verse_details
```

### Custom Pipeline

```python
# Create pipeline with only specific steps
pipeline = PipelineOrchestrator.create_partial_pipeline(
    step_names=[
        'AudioResamplingStep',
        'SilenceDetectionStep',
        'ChunkTranscriptionStep'
    ],
    model=model,
    processor=processor,
    device=device
)

# Execute
context = pipeline.execute(context)
```

### Manual Pipeline Construction

```python
from app.pipeline.base import Pipeline
from app.pipeline.steps import AudioResamplingStep, SilenceDetectionStep

# Build pipeline manually
pipeline = Pipeline(name="CustomPipeline")
pipeline.add_step(AudioResamplingStep(target_sample_rate=16000))
pipeline.add_step(SilenceDetectionStep(min_silence_len=300))

# Execute
context = pipeline.execute(context)
```

### Partial Execution

```python
# Execute from a specific step (resume)
context = pipeline.execute_from(context, start_step='ChunkTranscriptionStep')

# Execute until a specific step (debug)
context = pipeline.execute_until(context, end_step='SilenceDetectionStep')
```

### Adding/Removing Steps

```python
# Add a step
from app.pipeline.steps import CustomStep
pipeline.add_step(CustomStep())

# Insert at specific position
pipeline.insert_step(2, CustomStep())

# Remove a step
pipeline.remove_step('ChunkMergingStep')

# Get step by name
step = pipeline.get_step('SilenceDetectionStep')
```

## Creating Custom Steps

To create a new pipeline step:

```python
from app.pipeline.base import PipelineStep, PipelineContext

class MyCustomStep(PipelineStep):
    """
    My custom processing step.
    
    Input (from context):
        - input_data: Description
    
    Output (to context):
        - output_data: Description
    """
    
    def __init__(self, param1, param2):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
    
    def validate_input(self, context: PipelineContext) -> bool:
        """Validate required inputs"""
        if not context.get('input_data'):
            self.logger.error("Missing input_data")
            return False
        return True
    
    def should_skip(self, context: PipelineContext) -> bool:
        """Optional: Add skip logic"""
        return context.get('skip_custom_step', False)
    
    def process(self, context: PipelineContext) -> PipelineContext:
        """Main processing logic"""
        input_data = context.get('input_data')
        
        # Your processing logic here
        output_data = self._do_processing(input_data)
        
        # Update context
        context.set('output_data', output_data)
        
        # Add debug info
        context.add_debug_info(self.name, {
            'processed_items': len(output_data)
        })
        
        return context
    
    def _do_processing(self, data):
        """Helper method"""
        # Implementation
        pass
```

## Configuration

Pipeline steps can be configured via the config dictionary:

```python
config = {
    # Audio resampling
    'target_sample_rate': 16000,
    
    # Silence detection
    'min_silence_len': 500,  # ms
    'silence_thresh': -40,   # dBFS
    'keep_silence': 200,     # ms
    
    # Chunk merging
    'min_chunk_duration': 3.0,  # seconds
    'min_silence_gap': 0.5,     # seconds
}

pipeline = PipelineOrchestrator.create_full_pipeline(
    model=model,
    processor=processor,
    device=device,
    quran_data=quran_data,
    config=config
)
```

## Monitoring & Debugging

### Execution Summary

```python
# Get pipeline summary
summary = PipelineOrchestrator.get_pipeline_summary(context)

print(f"Steps executed: {summary['steps_executed']}")
print(f"Total duration: {summary['total_duration']:.2f}s")

for step in summary['steps']:
    print(f"  {step['name']}: {step['status']} ({step['duration']:.2f}s)")
```

### Step Results

```python
# Access individual step results
for step_name, result in context.step_results.items():
    print(f"{step_name}:")
    print(f"  Status: {result['status']}")
    print(f"  Duration: {result['duration']:.2f}s")
    print(f"  Data: {result['data']}")
```

### Debug Data

```python
# Access debug information
for step_name, debug_info in context.debug_data.items():
    print(f"{step_name} debug info:")
    print(debug_info)
```

## Best Practices

### 1. **Single Responsibility**
Each step should do one thing well:
```python
# Good
class SilenceDetectionStep(PipelineStep):
    def process(self, context):
        # Only detect silence
        pass

# Bad
class SilenceDetectionAndTranscriptionStep(PipelineStep):
    def process(self, context):
        # Does too many things
        pass
```

### 2. **Immutability Where Possible**
Don't modify input data directly:
```python
# Good
def process(self, context):
    chunks = context.chunks.copy()
    merged = self._merge(chunks)
    context.chunks = merged
    return context

# Bad
def process(self, context):
    self._merge_in_place(context.chunks)  # Modifies original
    return context
```

### 3. **Clear Input/Output Contract**
Document what the step expects and produces:
```python
class MyStep(PipelineStep):
    """
    Clear documentation.
    
    Input (from context):
        - required_field: Description
        - optional_field: Description (optional)
    
    Output (to context):
        - output_field: Description
    """
```

### 4. **Proper Error Handling**
Let exceptions bubble up, they're caught by the pipeline:
```python
def process(self, context):
    if not self._validate_data(context.data):
        raise ValueError("Invalid data format")
    
    # Process...
    return context
```

### 5. **Logging**
Use the built-in logger:
```python
def process(self, context):
    self.logger.info(f"Processing {len(context.chunks)} chunks")
    self.logger.debug(f"Detailed info: {context.metadata}")
    return context
```

## Testing

### Unit Testing Steps

```python
import pytest
from app.pipeline.base import PipelineContext
from app.pipeline.steps import AudioResamplingStep

def test_audio_resampling():
    # Create step
    step = AudioResamplingStep(target_sample_rate=16000)
    
    # Create context
    context = PipelineContext(
        audio_array=np.random.rand(48000),
        sample_rate=48000
    )
    
    # Execute
    result = step.execute(context)
    
    # Assert
    assert result.sample_rate == 16000
    assert len(result.audio_array) == 16000
```

### Integration Testing

```python
def test_full_pipeline():
    pipeline = PipelineOrchestrator.create_full_pipeline(
        model=mock_model,
        processor=mock_processor,
        device='cpu',
        quran_data=mock_quran_data
    )
    
    context = PipelineContext(
        audio_array=test_audio,
        sample_rate=16000
    )
    
    result = pipeline.execute(context)
    
    assert result.final_transcription
    assert len(result.verse_details) > 0
```

## Performance Considerations

1. **Step Ordering**: Place fast steps before slow ones when possible
2. **Skip Logic**: Use `should_skip()` to avoid unnecessary processing
3. **Lazy Loading**: Load heavy resources only when needed
4. **Parallel Processing**: Steps are sequential, but you can parallelize within a step
5. **Memory Management**: Clear large data from context when no longer needed

## Migration from Old Code

Old code:
```python
# Old monolithic approach
result = transcription_service.transcribe_audio(audio, sr)
```

New code:
```python
# New modular approach (same interface!)
result = transcription_service.transcribe_audio(audio, sr)
# Internally uses the pipeline architecture
```

The API remains the same, but the implementation is now modular!

## Future Enhancements

Potential improvements to the pipeline architecture:

1. **Async Steps**: Support for async/await in steps
2. **Parallel Execution**: Run independent steps in parallel
3. **Caching**: Cache step results for repeated executions
4. **Rollback**: Ability to rollback failed steps
5. **Conditional Branching**: Different paths based on conditions
6. **Step Dependencies**: Explicit dependency declaration
7. **Pipeline Composition**: Combine multiple pipelines

## Summary

The new pipeline architecture provides:

- ✅ **10 modular steps** that can be easily modified
- ✅ **Clear interfaces** with PipelineContext
- ✅ **Easy testing** of individual steps
- ✅ **Flexible execution** (full, partial, from/until)
- ✅ **Built-in monitoring** and debugging
- ✅ **Production-ready** with proper error handling
- ✅ **Extensible** for future enhancements

The architecture follows SOLID principles and common design patterns, making it maintainable and scalable for future development.

---

**For implementation details, see:**
- `app/pipeline/base.py` - Core abstractions
- `app/pipeline/orchestrator.py` - Factory and utilities
- `app/pipeline/steps/` - Individual step implementations
```
