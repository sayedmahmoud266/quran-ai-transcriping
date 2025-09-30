# Implementation Documentation

## Overview

This document describes the implementation details of the Quran AI Transcription API, including architecture, components, and technical decisions.

## Architecture

### High-Level Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request (audio file)
       ▼
┌─────────────────────────────────┐
│      FastAPI Application        │
│         (app/main.py)           │
└──────┬──────────────────────────┘
       │
       ├──► Audio Processor
       │    (app/audio_processor.py)
       │    - Format conversion
       │    - Resampling
       │    - Validation
       │
       ├──► Transcription Service
       │    (app/transcription_service.py)
       │    - Model loading
       │    - Transcription
       │    - Timestamp extraction
       │
       └──► Quran Data
            (app/quran_data.py)
            - Verse matching
            - Text normalization
            - Metadata retrieval
```

## Components

### 1. FastAPI Application (app/main.py)

**Purpose:** HTTP API layer that handles requests and responses.

**Key Features:**
- RESTful endpoints
- File upload handling
- Error handling and logging
- CORS support
- Automatic API documentation (Swagger/OpenAPI)

**Endpoints:**
- `GET /`: API information
- `GET /health`: Health check
- `POST /transcribe`: Main transcription endpoint

**Request Flow:**
1. Receive audio file upload
2. Validate file format
3. Save to temporary location
4. Process audio
5. Transcribe
6. Return results
7. Clean up temporary files

### 2. Audio Processor (app/audio_processor.py)

**Purpose:** Handle audio file processing and format conversion.

**Key Features:**
- Multi-format support (MP3, WAV, M4A, etc.)
- Automatic resampling to 16kHz (Whisper requirement)
- Mono conversion
- Audio validation

**Technologies:**
- `librosa`: Primary audio loading library
- `pydub`: Fallback for unsupported formats
- `soundfile`: Audio I/O

**Processing Pipeline:**
1. Try loading with librosa (fast path)
2. If fails, convert with pydub (compatibility)
3. Resample to 16kHz
4. Convert to mono
5. Validate audio data
6. Return numpy array

### 3. Transcription Service (app/transcription_service.py)

**Purpose:** Core transcription logic using the Whisper model.

**Key Features:**
- Model initialization and caching
- GPU/CPU automatic selection
- Timestamp extraction
- Verse detail generation

**Model Details:**
- **Name:** `tarteel-ai/whisper-base-ar-quran`
- **Base:** OpenAI Whisper Base
- **Specialization:** Arabic Quran recitations
- **Performance:** 5.75% WER

**Transcription Pipeline:**
1. Load and cache model (once at startup)
2. Process audio features
3. Generate transcription with timestamps
4. Extract word-level timestamps
5. Match to Quran verses
6. Return structured results

### 4. Quran Data (app/quran_data.py)

**Purpose:** Quran verse matching and metadata handling.

**Key Features:**
- Arabic text normalization
- Verse matching (placeholder for full implementation)
- Timestamp formatting
- Word counting

**Current Implementation:**
- Basic text normalization
- Placeholder verse matching
- Timestamp utilities

**Future Enhancements:**
- Integration with Quran database (Tanzil, quran-json)
- Fuzzy matching for verse detection
- Multiple recitation style support
- Tajweed rule detection

## Technical Decisions

### 1. Framework Choice: FastAPI

**Reasons:**
- High performance (async support)
- Automatic API documentation
- Type hints and validation
- Easy to use and deploy
- Modern Python features

### 2. Model: tarteel-ai/whisper-base-ar-quran

**Reasons:**
- Specifically fine-tuned for Quran
- Low WER (5.75%)
- Based on proven Whisper architecture
- Good balance of speed and accuracy
- Open source and accessible

### 3. Audio Processing: librosa + pydub

**Reasons:**
- `librosa`: Fast, efficient, widely used
- `pydub`: Broad format support, fallback option
- Combined approach ensures maximum compatibility

### 4. Deployment: Virtual Environment

**Reasons:**
- Isolated dependencies
- Reproducible setup
- Easy to manage
- Standard Python practice

## Data Flow

### Transcription Request Flow

```
1. Client uploads audio file
   ↓
2. FastAPI receives multipart/form-data
   ↓
3. Save to temporary file
   ↓
4. AudioProcessor.process_audio_file()
   ├─ Load audio
   ├─ Convert format if needed
   ├─ Resample to 16kHz
   └─ Return numpy array
   ↓
5. TranscriptionService.transcribe_audio()
   ├─ Validate audio
   ├─ Process with Whisper model
   ├─ Extract transcription
   ├─ Extract timestamps
   └─ Match verses
   ↓
6. Format response
   ↓
7. Return JSON to client
   ↓
8. Clean up temporary files
```

## Performance Optimization

### 1. Model Caching
- Model loaded once at startup
- Kept in memory for all requests
- Reduces latency significantly

### 2. GPU Acceleration
- Automatic GPU detection
- Falls back to CPU if unavailable
- ~10x faster on GPU

### 3. Async Processing
- FastAPI handles requests asynchronously
- Multiple concurrent requests supported
- Non-blocking I/O operations

### 4. Efficient Audio Processing
- Direct numpy array handling
- Minimal format conversions
- Streaming where possible

## Error Handling

### Levels of Error Handling

1. **Input Validation**
   - File format check
   - File size limits
   - Audio validity

2. **Processing Errors**
   - Audio conversion failures
   - Model errors
   - Timeout handling

3. **System Errors**
   - Out of memory
   - Disk space issues
   - Model loading failures

### Error Response Format

```json
{
  "detail": "Descriptive error message"
}
```

## Logging

### Log Levels

- **INFO**: Normal operations, requests, responses
- **WARNING**: Non-critical issues, fallbacks
- **ERROR**: Errors that need attention

### Logged Events

- API startup/shutdown
- Model loading
- Request processing
- Audio processing steps
- Transcription results
- Errors and exceptions

## Security Considerations

### Current Implementation

- No authentication (development mode)
- CORS enabled for all origins
- File size limits (implicit)
- Temporary file cleanup

### Production Recommendations

1. **Authentication**
   - API key authentication
   - OAuth2 support
   - Rate limiting per user

2. **Input Validation**
   - Strict file size limits
   - File type validation
   - Malware scanning

3. **CORS**
   - Restrict allowed origins
   - Specific allowed methods
   - Credential handling

4. **Rate Limiting**
   - Per-IP limits
   - Per-user limits
   - Burst protection

5. **Monitoring**
   - Request logging
   - Error tracking
   - Performance metrics

## Testing Strategy

### Unit Tests (Recommended)

```python
# Test audio processor
def test_audio_processor_mp3():
    audio, sr = audio_processor.process_audio_file("test.mp3")
    assert sr == 16000
    assert len(audio) > 0

# Test transcription service
def test_transcription_service():
    result = transcription_service.transcribe_audio(audio_array, 16000)
    assert result["success"] == True
    assert "exact_transcription" in result["data"]
```

### Integration Tests (Recommended)

```python
# Test full API endpoint
def test_transcribe_endpoint():
    with open("test_audio.mp3", "rb") as f:
        response = client.post(
            "/transcribe",
            files={"audio_file": f}
        )
    assert response.status_code == 200
    assert response.json()["success"] == True
```

## Deployment

### Development

```bash
./setup.sh
./run.sh
```

### Production (Recommended)

```bash
# Using gunicorn with uvicorn workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

### Docker (Future)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Configuration

### Environment Variables (Recommended)

```bash
# .env file
MODEL_NAME=tarteel-ai/whisper-base-ar-quran
MAX_FILE_SIZE=52428800  # 50MB
TEMP_DIR=/tmp
LOG_LEVEL=INFO
```

### Configuration File (Future)

```yaml
# config.yaml
model:
  name: tarteel-ai/whisper-base-ar-quran
  device: auto  # auto, cpu, cuda

audio:
  max_file_size: 52428800
  supported_formats:
    - mp3
    - wav
    - m4a

api:
  host: 0.0.0.0
  port: 8000
  workers: 4
```

## Future Improvements

### Short Term
1. Add proper Quran database integration
2. Implement comprehensive testing
3. Add request validation with Pydantic models
4. Improve error messages
5. Add API documentation examples

### Medium Term
1. Batch processing support
2. WebSocket for streaming
3. Confidence scores
4. Multiple recitation styles
5. Docker deployment

### Long Term
1. Microservices architecture
2. Distributed processing
3. Real-time transcription
4. Mobile app support
5. Multi-language support

## Maintenance

### Regular Tasks
- Update dependencies
- Monitor model performance
- Review logs for errors
- Update documentation
- Security patches

### Monitoring Metrics
- Request count
- Average response time
- Error rate
- Model accuracy
- Resource usage (CPU, GPU, memory)

## Dependencies

### Core Dependencies
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `transformers`: Hugging Face models
- `torch`: PyTorch for model inference
- `librosa`: Audio processing
- `pydub`: Audio format conversion

### Version Compatibility
- Python: 3.8+
- PyTorch: 2.1.1
- Transformers: 4.35.2
- FastAPI: 0.104.1

See `requirements.txt` for complete dependency list.

## Troubleshooting

### Common Issues

1. **Model fails to load**
   - Check internet connection
   - Verify Hugging Face access
   - Check disk space

2. **Audio processing fails**
   - Verify file format
   - Check file corruption
   - Install ffmpeg for pydub

3. **Out of memory**
   - Reduce concurrent requests
   - Use CPU instead of GPU
   - Process shorter audio files

4. **Slow transcription**
   - Enable GPU acceleration
   - Reduce audio quality
   - Optimize model settings

## Contact and Support

For technical questions or issues:
- Check documentation
- Review logs
- Open GitHub issue
- Contact maintainers
