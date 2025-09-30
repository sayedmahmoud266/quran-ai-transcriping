---
description: update workflow by splitting the audio into smaller chunks first then process it piece by piece
auto_execution_mode: 1
---

# Role
You are a highly skilled python developer

# Task
your task is to update the current code base to do the following:
- after receiving the audio file, use an appropriate library to split the audio file into smaller chunks by detecting the silences between speach.
- keep track of each chunk and it's relation to the entire audio
- pass the chunks piece by piece into the transcription model to get smaller and hopefully more accurate results
- add all the results together at the end and return the same response schema as before