# API Documentation

## Overview

The Quran AI Transcription API provides a simple HTTP interface for transcribing Quran recitations from audio files. The API is built with FastAPI and uses the `tarteel-ai/whisper-base-ar-quran` model for accurate transcription.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. In production, consider adding API key authentication or OAuth2.

## Endpoints

### 1. Root Endpoint

**Endpoint:** `GET /`

**Description:** Returns basic information about the API.

**Response:**
```json
{
  "message": "Quran AI Transcription API",
  "version": "1.0.0",
  "endpoints": {
    "POST /transcribe": "Upload audio file for transcription",
    "GET /health": "Health check endpoint"
  }
}
```

**Status Codes:**
- `200 OK`: Success

---

### 2. Health Check

**Endpoint:** `GET /health`

**Description:** Check the health status of the API and get model information.

**Response:**
```json
{
  "status": "healthy",
  "model": "tarteel-ai/whisper-base-ar-quran",
  "device": "cuda"
}
```

**Status Codes:**
- `200 OK`: API is healthy

---

### 3. Transcribe Audio

**Endpoint:** `POST /transcribe`

**Description:** Transcribe Quran recitation from an audio file.

**Request:**

- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `audio_file` (file, required): Audio file containing Quran recitation

**Supported Audio Formats:**
- MP3 (`.mp3`)
- WAV (`.wav`)
- M4A (`.m4a`)
- WMA (`.wma`)
- AAC (`.aac`)
- FLAC (`.flac`)
- OGG (`.ogg`)
- OPUS (`.opus`)
- WebM (`.webm`)

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "exact_transcription": "بسم الله الرحمن الرحيم الحمد لله رب العالمين",
    "details": [
      {
        "surah_number": 1,
        "ayah_number": 1,
        "ayah_text_tashkeel": "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
        "ayah_word_count": 4,
        "start_from_word": 1,
        "end_to_word": 4,
        "audio_start_timestamp": "00:00:00.000",
        "audio_end_timestamp": "00:00:02.500"
      },
      {
        "surah_number": 1,
        "ayah_number": 2,
        "ayah_text_tashkeel": "الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ",
        "ayah_word_count": 4,
        "start_from_word": 1,
        "end_to_word": 4,
        "audio_start_timestamp": "00:00:02.500",
        "audio_end_timestamp": "00:00:05.000"
      }
    ]
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

**Status Codes:**
- `200 OK`: Transcription successful
- `400 Bad Request`: Invalid input (unsupported format, no file, etc.)
- `500 Internal Server Error`: Server error during processing

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether the transcription was successful |
| `data` | object | Container for transcription data (only if success=true) |
| `data.exact_transcription` | string | The exact transcribed text from the audio |
| `data.details` | array | Array of verse details with timestamps |
| `error` | string | Error message (only if success=false) |

**Verse Detail Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `surah_number` | integer | Surah (chapter) number (1-114) |
| `ayah_number` | integer | Ayah (verse) number within the surah |
| `ayah_text_tashkeel` | string | Full verse text with tashkeel (diacritics) |
| `ayah_word_count` | integer | Total number of words in the verse |
| `start_from_word` | integer | Starting word index in the verse (1-based) |
| `end_to_word` | integer | Ending word index in the verse (1-based) |
| `audio_start_timestamp` | string | Start time in format "HH:MM:SS.mmm" |
| `audio_end_timestamp` | string | End time in format "HH:MM:SS.mmm" |

---

## Examples

### cURL Example

```bash
# Health check
curl http://localhost:8000/health

# Transcribe audio
curl -X POST "http://localhost:8000/transcribe" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio_file=@recitation.mp3"
```

### Python Example

```python
import requests

# Health check
response = requests.get("http://localhost:8000/health")
print(response.json())

# Transcribe audio
url = "http://localhost:8000/transcribe"
files = {"audio_file": open("recitation.mp3", "rb")}
response = requests.post(url, files=files)
result = response.json()

if result["success"]:
    print("Transcription:", result["data"]["exact_transcription"])
    for detail in result["data"]["details"]:
        print(f"Surah {detail['surah_number']}, Ayah {detail['ayah_number']}")
        print(f"  Text: {detail['ayah_text_tashkeel']}")
        print(f"  Time: {detail['audio_start_timestamp']} - {detail['audio_end_timestamp']}")
else:
    print("Error:", result["error"])
```

### JavaScript Example

```javascript
// Health check
fetch('http://localhost:8000/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Transcribe audio
const formData = new FormData();
formData.append('audio_file', fileInput.files[0]);

fetch('http://localhost:8000/transcribe', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(result => {
  if (result.success) {
    console.log('Transcription:', result.data.exact_transcription);
    result.data.details.forEach(detail => {
      console.log(`Surah ${detail.surah_number}, Ayah ${detail.ayah_number}`);
      console.log(`  ${detail.ayah_text_tashkeel}`);
    });
  } else {
    console.error('Error:', result.error);
  }
});
```

## Error Handling

The API uses standard HTTP status codes and returns error messages in JSON format.

### Common Errors

| Status Code | Error | Cause |
|-------------|-------|-------|
| 400 | No audio file provided | Request missing audio_file parameter |
| 400 | Unsupported audio format | File format not in supported list |
| 400 | Error processing audio file | Audio file is corrupted or invalid |
| 500 | Error during transcription | Model error or internal server error |

### Error Response Format

```json
{
  "detail": "Error message describing the issue"
}
```

## Rate Limiting

Currently, there is no rate limiting implemented. In production, consider adding rate limiting to prevent abuse.

## Performance Considerations

### Audio File Size
- Recommended: < 10MB
- Maximum: 50MB (configurable)
- Longer audio files take more time to process

### Processing Time
- Typical: 0.1x - 0.3x real-time (e.g., 10-second audio takes 1-3 seconds)
- Depends on:
  - Audio length
  - CPU/GPU performance
  - Server load

### Concurrent Requests
- The API can handle multiple concurrent requests
- Each request is processed independently
- GPU memory may limit concurrent processing

## Best Practices

1. **Audio Quality**: Use high-quality audio for best results (16kHz or higher)
2. **File Format**: WAV or FLAC provide best quality, MP3 is acceptable
3. **Error Handling**: Always check the `success` field in the response
4. **Timeouts**: Set appropriate timeouts for longer audio files
5. **Retry Logic**: Implement retry logic for transient errors

## Future Enhancements

Planned features for future versions:
- Batch processing of multiple files
- Streaming audio support
- WebSocket support for real-time transcription
- Authentication and API keys
- Rate limiting
- Improved verse matching with Quran database integration
- Support for different Quran recitation styles
- Confidence scores for transcriptions

## Support

For issues or questions about the API, please refer to the main README or open an issue in the repository.
