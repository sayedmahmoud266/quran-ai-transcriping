---
description: Update silence detection algorithms and verse detection algorithms
auto_execution_mode: 1
---

You should update the verse detection algorithm and the silence detection algorithm to do the following:
- after receiving the audio and normalizing it (transcoding, changing sample rate) then:
  - proceed to detect silences as normal but (do not merge resulted chunks together unless they're less than 3 seconds, anything longer should not be merged together)
  - proceed with transcoding of each chunk throw the whisper model, and add the resulted text to the chunk object to keep track of which text is generated from which chunk. for example:
   {chunk: 1, transcribed_text: 'بسم الله الرحمن الرحيم'},{chunk: 2, transcribed_trext: 'الم'},{chunk: 3, transcribed_text: 'ذلك الكتب لاريب'},{chunk: 4, transcribed_text: 'فيه هدى للمتقين'}
  - make sure when you create the combined text of all chunks that you remove any duplicate words from the end and the start of each consecutive chunks. for example:
   {chunk: 300, transcribed_text: ' وَكَذَٰلِكَ يَجۡتَبِيكَ رَبُّكَ وَيُعَلِّمُكَ مِن تَأۡوِيلِ ٱلۡأَحَادِيثِ وَيُتِمُّ نِعۡمَتَهُۥ عَلَيۡكَ وَعَلَىٰٓ ءَالِ يَعۡقُوبَ'},{chunk: 301, transcribed_text: 'وَيُتِمُّ نِعۡمَتَهُۥ عَلَيۡكَ وَعَلَىٰٓ ءَالِ يَعۡقُوبَ كَمَآ أَتَمَّهَا عَلَىٰٓ أَبَوَيۡكَ مِن قَبۡلُ إِبۡرَٰهِيمَ وَإِسۡحَٰقَۚ إِنَّ رَبَّكَ عَلِيمٌ حَكِيمٞ'}
    -> notice how 'وَيُتِمُّ نِعۡمَتَهُۥ عَلَيۡكَ وَعَلَىٰٓ ءَالِ يَعۡقُوبَ' is repeated in 2 chunks. these should be added only once and detected only once. to enhance the matching score of the ayah.
  - also note that one chunk can easily contain multiple ayahs, for example:
   {chunk: 1, transcribed_text: 'الرحمن علم القران خلق الانسان علمه البيان الشمس و القمر بحسبان والنجم و الشجر يسجدان والسماء رفعها ووضع الميزان'}
    -> notice how this chunk contains 7 consecutive ayahs, which is completly normal. and this chunk should be linked to all these 7 ayahs
  - after that you proceed with the verse matching process as it currently is with no change to detect the surah and the start and end of this entire input audio.
- after you already linked the found ayahs with the chunks which is a many to many relationship you do the following for the timestamps detection of each ayah:
  - if the ayah completly enclosed in only one chunk (meaning the chunk only include this ayah completly, and no other parts of other ayahs), then use this chunk boundaries as the ayah boundaries.
  - if the ayah completly enclosed on more than one chunk (meaning a set of consecutive chunks start with the start of the ayah and end with the end of the ayah with no other parts of other ayahs), use the start of the first chunk and the end of the last chunk as the boundaries of the ayah.
  - if the ayah enclosed in only one chunk but with other parts of other ayahs with it, then [just for now], split the chunk time evenly between it's word count and extract the ayah time boundaries based on the relation of it's word count to the entire chunk word count
  - if the ayah spans accross multiple chunks with other parts of other ayahs with it [even if parts of them are repeated], then [just for now], splut each chunk time evenly between it's word count and extract the ayah time boundaries by using the start of the first occurance of the first word of the ayah, and the end of the  last occurance of the last word of the ayah as the full ayah boundary.
- proceed with splitting all silences in half between consecutive ayahs as before ONLY IF ayahs split point happens at the start and end of 2 consecutive chunks, otherwise if the split point was in the middle of any chunk then keep 0ms between them without adding any silences or changing the split point.
- remove the current logic of gaps detection inside ayahs, and replace it with ayah_chunks. which should include all the chunks (or parts of chunks) that are used to form the whole ayah, with mentioning the start_word, and end_word of each chunk, to handle repeated words and overlapping words between ayahs.