# Changelog

All notable changes to the Quran AI Transcription API project.

## [2.2.0] - 2025-10-03

### Added
- **Intelligent Gap Detection**: Advanced silence-based split point detection for consecutive ayahs
  - Automatic detection of 0ms gaps between ayahs
  - Secondary silence search (±10 seconds) around problematic cutoff points
  - Uses closest silence gap midpoint for optimal splitting
  - Uncertainty flagging when no silence found
- **Enhanced Metadata**: New `cutoff_uncertain` field in metadata.json
  - Flags ayahs with uncertain split points for manual review
  - Helps identify potential audio quality issues

### Changed
- `_calculate_adjusted_timestamps()` now accepts audio segment for silence detection
- Returns 3-tuple timestamps: `(start_ms, end_ms, uncertain_flag)`
- Enhanced logging with detailed silence search information

### Fixed
- 🐛 **Critical**: Fixed mid-sentence ayah cuts in continuous recitations
- 🐛 **Critical**: Prevented long ayah truncation (e.g., Surah 12, Ayah 6)
- 🐛 Improved split point accuracy for ayahs without natural pauses

### Technical Details
- New method: `_find_silence_near_cutoff()` for intelligent gap detection
- Search window: ±10 seconds from cutoff point
- Silence detection: 500ms minimum, -40dBFS threshold
- Automatically adjusts both current and previous ayah boundaries

## [1.3.0] - 2025-10-01

### Added
- **Multi-Ayah Detection**: Now detects and returns multiple consecutive verses in a single audio
- **Basmala Handling**: Special handling for "بسم الله الرحمن الرحيم" (Basmala)
  - Automatically detected at the start of recitations
  - Returns `ayah_number: 0` for Basmala in all surahs except Surah 1
  - Returns `ayah_number: 1` for Basmala in Surah 1 (Al-Fatiha)
  - Includes `is_basmala: true` flag in response
- **Consecutive Verse Matching**: Intelligently finds sequences of verses in continuous recitation
- **Improved Timing Distribution**: Better timestamp allocation across multiple verses

### Changed
- Enhanced `_find_consecutive_verses()` to detect verse sequences
- Added `_is_basmala()` for Basmala detection
- Added `_find_verse_sequence()` for sequential verse matching
- Added `_get_verse_by_key()` helper method
- Improved verse matching to handle multi-verse audio
- Better time distribution across detected verses

### Fixed
- Now correctly identifies multiple verses instead of just one
- Proper Basmala numbering based on surah context
- Better handling of continuous recitations without clear pauses

## [1.2.0] - 2025-10-01

### Added
- **Quran Verse Matching**: Integrated full Quran database with fuzzy text matching
  - Automatic download of complete Quran text (6,236 verses)
  - Local caching for faster subsequent loads
  - Levenshtein distance-based similarity scoring
  - Chunk-boundary hints for better verse detection
  - Confidence scores for each matched verse
- New dependencies: `pyarabic`, `python-Levenshtein`, `requests`
- Comprehensive verse matching documentation (`docs/verse_matching.md`)
- Fallback Quran data (Surah Al-Fatiha) if download fails

### Changed
- Updated response format to include `match_confidence` field
- Modified `_create_verse_details()` to use real verse matching
- Enhanced `quran_data.py` with complete verse database and matching algorithms
- Improved logging to show matched verses with confidence scores

### Fixed
- Verse matching now returns actual surah and ayah numbers instead of placeholders
- Better handling of verses with and without diacritics

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
