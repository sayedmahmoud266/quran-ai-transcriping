---
description: Multi Ayah
auto_execution_mode: 1
---

it currently only detects one ayah, update the logic to be able to detect consecutive ayahs, and keep in mind that "بسم الله الرحمن الرحيم" exists on the start on every surah, and usually does not have an ayah number, instead should detect the current surah using the next ayah or next chunk, and then giving it ayah_number: 0, unless the detected surah was actually surah_number: 1, then it should be ayah_number: 1