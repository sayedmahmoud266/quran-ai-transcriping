---
description: Split input audio into single ayahs
auto_execution_mode: 1
---

# Role
You are a highly skilled python developer

# Task
Your task is to add an option or a flag to be passed in the transcribe request named "split_audio", it should be boolean and not required by default.
but in case if it was passed with the value "true" it should do the following:
- after finishing transcribing the entire surah, then it uses the generated timestamps of each ayah (start & end), and use the original uploaded track (for best quality possible) and extract from it all ayahs in the same format as the input audio, and prepare them in a .zip file, and allow the user to download it.

# Condition
create a new feat-exp/* branch to work on this feature in a separate version and if it worked we will merge it to master later