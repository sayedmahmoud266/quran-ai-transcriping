# Audio Splitting Feature

## Overview

The audio splitting feature allows you to extract individual ayah segments from the original audio file after transcription. This is useful for:
- Creating ayah-by-ayah audio collections
- Building Quran learning applications
- Generating audio flashcards
- Creating custom playlists

## How It Works

1. Upload an audio file containing Quran recitation
2. Set `split_audio=true` in the request
3. The API transcribes the audio and identifies all ayahs
4. Each ayah is extracted from the original audio file (best quality)
5. All ayah segments are packaged into a ZIP file
6. The ZIP file is returned for download

## API Usage

### Endpoint

```
POST /transcribe
```

### Parameters

- `audio_file` (file, required): Audio file containing Quran recitation
- `split_audio` (boolean, optional, default=false): Enable audio splitting

### Example Requests

#### Using cURL

```bash
curl -X POST "http://localhost:8000/transcribe" \
  -H "accept: application/zip" \
  -F "audio_file=@surah_55.mp3" \
  -F "split_audio=true" \
  --output surah_55_ayahs.zip
```

#### Using Python requests

```python
import requests

url = "http://localhost:8000/transcribe"
files = {"audio_file": open("surah_55.mp3", "rb")}
data = {"split_audio": "true"}

response = requests.post(url, files=files, data=data)

# Save the zip file
with open("surah_55_ayahs.zip", "wb") as f:
    f.write(response.content)
```

#### Using JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('audio_file', audioFile);
formData.append('split_audio', 'true');

fetch('http://localhost:8000/transcribe', {
  method: 'POST',
  body: formData
})
.then(response => response.blob())
.then(blob => {
  // Create download link
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'quran_ayahs.zip';
  a.click();
});
```

## ZIP File Structure

The returned ZIP file contains:

```
surah_055_ayahs.zip
├── surah_055_basmala.mp3          # Basmala (if present)
├── surah_055_ayah_001.mp3         # First ayah
├── surah_055_ayah_002.mp3         # Second ayah
├── ...
├── surah_055_ayah_078.mp3         # Last ayah
└── README.txt                      # Information file
```

### File Naming Convention

- **Basmala**: `surah_XXX_basmala.{ext}`
- **Regular Ayahs**: `surah_XXX_ayah_YYY.{ext}`

Where:
- `XXX` = Surah number (3 digits, zero-padded)
- `YYY` = Ayah number (3 digits, zero-padded)
- `{ext}` = Original audio format (mp3, wav, m4a, etc.)

### README.txt Contents

Each ZIP file includes a README with:
- Surah number
- Total ayahs count
- Audio format
- File naming explanation
- API information

## Supported Audio Formats

The feature preserves the original audio format:
- ✅ MP3 (.mp3) - 192kbps bitrate
- ✅ WAV (.wav) - Original quality
- ✅ M4A (.m4a) - AAC format
- ✅ OGG (.ogg) - Vorbis format
- ✅ FLAC (.flac) - Lossless
- ✅ Other formats - Converted to WAV

## Quality Preservation

- **Source**: Original uploaded audio file (not resampled)
- **Extraction**: Precise timestamp-based cutting
- **Encoding**: Format-specific optimal settings
- **MP3**: 192kbps bitrate for quality/size balance
- **Lossless**: FLAC and WAV maintain original quality

## Performance

| Metric | Value |
|--------|-------|
| **Processing Time** | +2-5 seconds (after transcription) |
| **ZIP Size** | ~80-90% of original file size |
| **Quality Loss** | Minimal (format-dependent) |
| **Memory Usage** | +100-200 MB during splitting |

### Example Timings

**Surah 55 (Ar-Rahman) - 20 minutes audio:**
- Transcription: ~20 seconds
- Audio splitting: ~3 seconds
- ZIP creation: ~1 second
- **Total**: ~24 seconds

## Error Handling

### No Ayahs Detected

If transcription fails to detect any ayahs:
```json
{
  "detail": "No ayah details found in transcription. Cannot split audio."
}
```

### Audio Processing Error

If audio splitting fails:
```json
{
  "detail": "Error splitting audio: [error message]"
}
```

### Unsupported Format

If audio format is not supported:
```json
{
  "detail": "Unsupported audio format: .xyz"
}
```

## Use Cases

### 1. Quran Learning App

```python
# Download and split a surah
response = requests.post(
    "http://localhost:8000/transcribe",
    files={"audio_file": open("surah.mp3", "rb")},
    data={"split_audio": "true"}
)

# Extract and use individual ayahs
with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    for filename in z.namelist():
        if filename.endswith('.mp3'):
            ayah_audio = z.read(filename)
            # Use in your app
```

### 2. Ayah Memorization Tool

```python
# Get ayah segments for memorization practice
import zipfile
import io

response = requests.post(url, files=files, data={"split_audio": "true"})

with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    # Play ayahs one by one for memorization
    for ayah_file in sorted(z.namelist()):
        if 'ayah' in ayah_file:
            audio_data = z.read(ayah_file)
            play_audio(audio_data)
            wait_for_user_input()
```

### 3. Custom Playlist Generator

```python
# Create a custom playlist of specific ayahs
with zipfile.ZipFile('surah_55_ayahs.zip') as z:
    selected_ayahs = [
        'surah_055_ayah_001.mp3',
        'surah_055_ayah_013.mp3',  # Repeated phrase
        'surah_055_ayah_078.mp3'
    ]
    
    for ayah in selected_ayahs:
        audio = z.read(ayah)
        add_to_playlist(audio)
```

## Technical Implementation

### Audio Splitter Module

Located in `app/audio_splitter.py`:

```python
class AudioSplitter:
    def split_audio_by_ayahs(
        self,
        audio_file_path: str,
        ayah_details: List[Dict]
    ) -> Tuple[io.BytesIO, str]:
        """
        Split audio file into individual ayah segments.
        
        Returns:
            (zip_buffer, zip_filename)
        """
```

### Timestamp Parsing

Converts timestamp format `HH:MM:SS.mmm` to milliseconds:
```python
def _parse_timestamp(self, timestamp: str) -> int:
    time_part, ms_part = timestamp.split('.')
    hours, minutes, seconds = map(int, time_part.split(':'))
    milliseconds = int(ms_part)
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + milliseconds
```

### Audio Extraction

Uses pydub for precise audio segment extraction:
```python
audio = AudioSegment.from_mp3(audio_file_path)
segment = audio[start_ms:end_ms]
segment.export(buffer, format='mp3', bitrate='192k')
```

## Limitations

1. **Single Surah Only**: Currently supports one surah per audio file
2. **Complete Ayahs**: Assumes full ayahs (no partial detection)
3. **Sequential Order**: Ayahs must be in order in the audio
4. **Memory Usage**: Large files may require significant memory

## Future Enhancements

- [ ] Batch processing (multiple surahs)
- [ ] Custom bitrate selection
- [ ] Format conversion options
- [ ] Ayah metadata in filenames
- [ ] Parallel processing for faster splitting
- [ ] Streaming ZIP generation for large files

## Troubleshooting

### ZIP File is Corrupt

- Check available disk space
- Verify original audio file is not corrupted
- Try with a smaller audio file first

### Missing Ayahs in ZIP

- Check transcription accuracy first (without split_audio)
- Verify all ayahs have valid timestamps
- Check logs for splitting errors

### Poor Audio Quality

- Use lossless formats (FLAC, WAV) for best quality
- Ensure original audio is high quality
- MP3 uses 192kbps bitrate by default

## Version History

- **v2.1.0** (feat-exp/split-audio-by-ayah): Initial implementation
  - Basic audio splitting functionality
  - ZIP file generation
  - Format preservation
  - README generation

---

**Branch**: feat-exp/split-audio-by-ayah  
**Status**: Experimental  
**Last Updated**: October 2025
