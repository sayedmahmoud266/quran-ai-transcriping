# Quran AI Transcription API

A Python-based HTTP API for transcribing Quran recitations from audio files using the `tarteel-ai/whisper-base-ar-quran` model from Hugging Face.

## Features

- **Multi-format Audio Support**: Accepts various audio formats (MP3, WAV, M4A, WMA, AAC, FLAC, OGG, OPUS, WebM)
- **Intelligent Audio Chunking**: Automatically splits audio by silence detection for improved accuracy
- **Automatic Audio Processing**: Handles different sample rates and converts to the required format
- **Fast Transcription**: Uses the fine-tuned Whisper model optimized for Quran recitations
- **Detailed Output**: Returns transcription with verse details and timestamps
- **RESTful API**: Simple HTTP API built with FastAPI

## Requirements

- Python 3.8 or higher
- Virtual environment support
- At least 2GB RAM (4GB+ recommended)
- GPU support optional (CUDA-compatible GPU for faster processing)

## Installation

### 1. Clone or navigate to the repository

```bash
cd /path/to/tarteel-ai_whisper-base-ar-quran
```

### 2. Run the setup script

```bash
chmod +x setup.sh
./setup.sh
```

This will:
- Create a virtual environment
- Install all required dependencies
- Set up the project for running

### 3. Activate the virtual environment

```bash
source venv/bin/activate
```

## Usage

### Starting the Server

#### Option 1: Using the run script (recommended)

```bash
chmod +x run.sh
./run.sh
```

#### Option 2: Manual start

```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### API Endpoints

#### 1. Root Endpoint
```
GET /
```
Returns API information and available endpoints.

#### 2. Health Check
```
GET /health
```
Returns the health status of the API and model information.

#### 3. Transcribe Audio
```
POST /transcribe
```

**Parameters:**
- `audio_file` (file, required): Audio file containing Quran recitation

**Supported Audio Formats:**
- MP3 (.mp3)
- WAV (.wav)
- M4A (.m4a)
- WMA (.wma)
- AAC (.aac)
- FLAC (.flac)
- OGG (.ogg)
- OPUS (.opus)
- WebM (.webm)

**Response Format:**
```json
{
  "success": true,
  "data": {
    "exact_transcription": "بسم الله الرحمن الرحيم",
    "details": [
      {
        "surah_number": 1,
        "ayah_number": 1,
        "ayah_text_tashkeel": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "ayah_word_count": 4,
        "start_from_word": 1,
        "end_to_word": 4,
        "audio_start_timestamp": "00:00:00.000",
        "audio_end_timestamp": "00:00:03.500"
      }
    ]
  }
}
```

### Example Usage

#### Using cURL

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio_file=@/path/to/quran_recitation.mp3"
```

#### Using Python requests

```python
import requests

url = "http://localhost:8000/transcribe"
files = {"audio_file": open("quran_recitation.mp3", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

#### Using JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('audio_file', audioFile);

fetch('http://localhost:8000/transcribe', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── audio_processor.py         # Audio processing utilities
│   ├── transcription_service.py   # Transcription logic
│   └── quran_data.py             # Quran verse matching utilities
├── docs/
│   ├── model_readme.md              # Model documentation
│   ├── api_documentation.md         # API documentation
│   ├── implementation.md            # Technical implementation details
│   └── chunking_implementation.md   # Audio chunking documentation
├── .gitignore
├── requirements.txt              # Python dependencies
├── setup.sh                      # Setup script
├── run.sh                        # Run script
└── README.md                     # This file
```

## Model Information

This API uses the `tarteel-ai/whisper-base-ar-quran` model, which is a fine-tuned version of OpenAI's Whisper model specifically optimized for Quran recitations.

**Model Performance:**
- WER (Word Error Rate): 5.75%
- Validation Loss: 0.0839

For more details, see [docs/model_readme.md](docs/model_readme.md)

## Development

### Running in Development Mode

The API runs with auto-reload enabled by default when using the run script, which means changes to the code will automatically restart the server.

### Adding Quran Database Integration

The current implementation includes placeholder logic for verse matching. To add proper Quran verse matching:

1. Integrate a Quran database (e.g., Tanzil, quran-json)
2. Update `app/quran_data.py` with actual verse matching logic
3. Implement fuzzy matching for better verse detection

### Performance Optimization

- **GPU Acceleration**: The API automatically uses GPU if available (CUDA)
- **Model Caching**: The model is loaded once at startup and reused for all requests
- **Async Processing**: FastAPI handles requests asynchronously for better throughput
- **Smart Chunking**: Audio is split by silence detection for better accuracy and memory efficiency

For more details on the chunking implementation, see [docs/chunking_implementation.md](docs/chunking_implementation.md)

## Troubleshooting

### Model Download Issues

If the model fails to download, ensure you have:
- Stable internet connection
- Sufficient disk space (~500MB for the model)
- Access to Hugging Face (not blocked by firewall)

### Audio Processing Errors

If audio processing fails:
- Ensure the audio file is not corrupted
- Check that the file format is supported
- Verify the file is not empty

### Memory Issues

If you encounter out-of-memory errors:
- Close other applications to free up RAM
- Consider using a smaller batch size
- Use GPU if available

## License

Apache 2.0 (inherited from the model license)

## Acknowledgments

- Model: [tarteel-ai/whisper-base-ar-quran](https://huggingface.co/tarteel-ai/whisper-base-ar-quran)
- Base Model: [OpenAI Whisper](https://github.com/openai/whisper)
- Framework: [FastAPI](https://fastapi.tiangolo.com/)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Support

For issues or questions, please open an issue in the repository.
