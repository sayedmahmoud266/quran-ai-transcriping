---
description: quran ai app
auto_execution_mode: 1
---

# Role
you are a highly skilled developed who's specialized in python apps and ai related applications

# Task
your task is to create a simple python application that can process any audio file containing quran recitations and return the transcription of said audio and the correct quran verses in that audio.

# Requirements
- the app must be usable through a simple http api that accepts the audio and return all the required data.
- the app must do so in a relatively fast and efficient time
- the app should use model `tarteel-ai/whisper-base-ar-quran` from huggingface to do the audio-to-quran text transcription


# Acceptance criteria
- the app must accept any form of audio file in any format or sampling rate, for example (mp3, wav, m4a, wma...etc)
- the app must return data according to the following json object
```json
{
  "success": true,
  "data": {
    "exact_transcription": "{predicted_quran_text_here}",
    "details": [
      {"surah_number": 2, "ayah_number": 1, "ayah_text_tashkeel": "الم", "ayah_word_count": 1, "start_from_word": 1, "end_to_word": 1, "audio_start_timestamp": "00:00:01.232", "audio_end_timestamp": "00:00:02.999"},
      {"surah_number": 2, "ayah_number": 2, "ayah_text_tashkeel": "ذلك الكتاب لا ريب فيه هدى للمتقين", "ayah_word_count": 7, "start_from_word": 1, "end_to_word": 7, "audio_start_timestamp": "00:00:03.232", "audio_end_timestamp": "00:00:10.999"},
      ...
    ]
  }
}
```