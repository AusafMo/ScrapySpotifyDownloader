### Basic Flow
---
  1. get Playlist metadata after going through brain melting cookie, token stuff.
  2. hit pytube with search.
  3. get the title, sort, filter based on 'version' etc
  4. download the youtube streams as mp4.
  5. zip mp4
  6. extract mp3 from mp4 using ffmpeg, zipIt-shipIt.
----
### TODO:
  1. Get better with the cookie and auth, its abomination rn.
  2. Get gud with async downloads, there's hungup tasks even after exiting.
  3. Look for more ffmpeg optional params to get from user, codec, bitrate etc.

### How to Run:
----
only gud thing bout this,
1. spin up collab, install all the requirements.txt dependencies
  `pip install -r requirements.txt`
2. copy run.py
3. shit+enter
4. get the gradio interface, enter PLAYLIST URL.

Takes 3-5 mins to generate zips for: [SamplePlaylist](https://open.spotify.com/playlist/4HC6d7aRLc34knclyf1aXx?si=abc3b81457be4523)

Note: to run locally install ffmpeg and set enviornment variable to the path.

This is purely a work of boredom, no misuse or any type of infringement on any works intended nor implied.
