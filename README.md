<img width="700" alt="image" src="https://github.com/user-attachments/assets/1d3e62e3-622b-4b35-a52b-ea1720719fa7">

### Basic Flow of Code
---
  1. get Playlist metadata after going through cookie, token stuff.
  2. hit pytube with search.
  3. get the title, sort, filter based on length, 'version' etc
  4. download the youtube streams as mp4.
  5. zip videos
  6. extract mp3 from mp4 using ffmpeg, zipIt-shipIt.
----
### TODO:
  1. Get better with the cookie and auth, its abomination rn.
  2. Get gud with async downloads, there's hungup tasks even after exiting.
  3. Look for more ffmpeg optional params to get from user, codec, bitrate etc.

### How to Run:
----
only gud thing bout this,
1. spin up collab notebook, change runtime to T4, install all the dependencies with
  `pip install -r requirements.txt`  or 
copy paste
```
!pip --q install pytube
!pip --q install aiohttp
!pip --q install nest-asyncio
!pip --q install moviepy
!pip --q install gradio
```
2. copy colab.py script
3. shift + enter
4. get the gradio interface, enter PLAYLIST URL.

Takes 2-3 mins to generate both zips for: [SamplePlaylist](https://open.spotify.com/playlist/4HC6d7aRLc34knclyf1aXx?si=abc3b81457be4523)

Note: to run locally install ffmpeg and set enviornment variable to the path.

This is purely a work of boredom, no misuse or any type of infringement on any works intended nor implied.
----
#### Apparently can't host it on render due to PyTube lib, (as far as i can tell, they are blocking PyTube lib requests), and I am NOT using railway.
