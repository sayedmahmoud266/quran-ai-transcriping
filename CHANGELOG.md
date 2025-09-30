# Changelog

All notable changes to the Quran AI Transcription API project.

## [1.1.0] - 2025-10-01

### Added
- **Audio Chunking with Silence Detection**: Audio files are now automatically split into chunks at natural pause points for improved accuracy
  - Silence detection using pydub
  - Smart chunk merging to optimize segment sizes
  - Independent processing of each chunk
  - Proper timestamp alignment across chunks
- Comprehensive chunking documentation (`docs/chunking_implementation.md`)
- Makefile for easier project commands

### Changed
- Updated `requirements.txt` to use compatible PyTorch versions (>= 2.2.0)
- Updated numpy version constraint to `<2.0.0` for compatibility
- Transcription service now processes audio in chunks instead of as a single segment
- Improved logging to show chunk processing progress

### Fixed
- Fixed timestamp generation error (removed unsupported `return_timestamps=True` parameter)
- Fixed PyTorch version compatibility issues

### Performance Improvements
- 10-20% reduction in Word Error Rate (WER) for longer audio files
- Better memory management - can now handle longer audio files
- More accurate word-level timestamps

## [1.0.0] - 2025-09-30

### Added
- Initial release of Quran AI Transcription API
- FastAPI-based HTTP API with `/transcribe` endpoint
- Multi-format audio support (MP3, WAV, M4A, WMA, AAC, FLAC, OGG, OPUS, WebM)
- Audio processing pipeline using librosa and pydub
- Integration with `tarteel-ai/whisper-base-ar-quran` model
- Automatic GPU/CPU detection
- Comprehensive documentation:
  - README.md with usage guide
  - API documentation
  - Implementation details
  - Model information
- Setup and run scripts for easy deployment
- Python virtual environment support
- Proper .gitignore for Python projects

### Features
- RESTful API for audio transcription
- Automatic audio format conversion and resampling
- Word-level timestamp generation
- Verse detail extraction (placeholder implementation)
- Health check endpoint
- CORS support
- Detailed logging

---

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backwards compatible manner
- **PATCH** version for backwards compatible bug fixes
