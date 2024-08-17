from bs4 import BeautifulSoup
from pytube import YouTube, Search, cipher
from moviepy.editor import VideoFileClip
import gradio as gr
import subprocess
import zipfile
import json
import requests
import re
import os
import time
import shutil

import asyncio
from concurrent.futures import ThreadPoolExecutor

import nest_asyncio
nest_asyncio.apply()

import logging
pytube_logger = logging.getLogger('pytube')
pytube_logger.setLevel(logging.ERROR)


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
)

def get_throttling_function_name(js: str) -> str:
    """Extract the name of the function that computes the throttling parameter.

    :param str js:
        The contents of the base.js asset file.
    :rtype: str
    :returns:
        The name of the function used to compute the throttling parameter.
    """
    function_patterns = [
        # https://github.com/ytdl-org/youtube-dl/issues/29326#issuecomment-865985377
        # https://github.com/yt-dlp/yt-dlp/commit/48416bc4a8f1d5ff07d5977659cb8ece7640dcd8
        # var Bpa = [iha];
        # ...
        # a.C && (b = a.get("n")) && (b = Bpa[0](b), a.set("n", b),
        # Bpa.length || iha("")) }};
        # In the above case, `iha` is the relevant function name
        r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&\s*'
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])\([a-z]\)',
    ]
    #logger.debug('Finding throttling function name')
    for pattern in function_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(js)
        if function_match:
            #logger.debug("finished regex search, matched: %s", pattern)
            if len(function_match.groups()) == 1:
                return function_match.group(1)
            idx = function_match.group(2)
            if idx:
                idx = idx.strip("[]")
                array = re.search(
                    r'var {nfunc}\s*=\s*(\[.+?\]);'.format(
                        nfunc=re.escape(function_match.group(1))),
                    js
                )
                if array:
                    array = array.group(1).strip("[]").split(",")
                    array = [x.strip() for x in array]
                    return array[int(idx)]

    raise RegexMatchError(
        caller="get_throttling_function_name", pattern="multiple"
    )

cipher.get_throttling_function_name = get_throttling_function_name

def getHeaders():
  cookie = None
  headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"}
  res = requests.get("https://open.spotify.com/", headers = headers)
  cookie = res.cookies
  cookie = '; '.join(['='.join(x) for x in list(cookie.items())])
  cookie

  headers = {
      "authority": "clienttoken.spotify.com",
      "method": "POST",
      "path": "/v1/clienttoken",
      "scheme": "https",
      "accept": "application/json",
      "accept-encoding": "gzip, deflate, br, zstd",
      "accept-language": "en-US,en;q=0.9",
      "cache-control": "no-cache",
      "content-length": "276",
      "content-type": "application/json",
      "origin": "https://open.spotify.com",
      "pragma": "no-cache",
      "priority": "u=1, i",
      "referer": "https://open.spotify.com/",
      "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
      "sec-ch-ua-mobile": "?0",
      "sec-ch-ua-platform": '"macOS"',
      "sec-fetch-dest": "empty",
      "sec-fetch-mode": "cors",
      "sec-fetch-site": "same-site",
      "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
  }
  headers['cookie'] = cookie

  return headers

def authStuff(purl, headers):

  playlistId = str(purl.split("/")[4].strip(""))

  html_content = requests.get(purl, headers)
  html_content = html_content.content

  soup = BeautifulSoup(html_content, 'html.parser')

  config_script = soup.find('script', {'id': 'config'}).string
  config_data = json.loads(config_script)
  correlation_id = config_data['correlationId']

  session_script = soup.find('script', {'id': 'session'}).string
  session_data = json.loads(session_script)
  client_id = session_data['clientId']
  bearer_token = f"Bearer {session_data['accessToken']}"

  return client_id, correlation_id, bearer_token, playlistId

def clientToken(client_id, headers):
  token = "https://clienttoken.spotify.com/v1/clienttoken"
  payload = {"client_data":{"client_version":"1.2.44.216.g1fe6e17d","client_id":client_id,"js_sdk_data":{"device_brand":"Apple","device_model":"unknown","os":"macos","os_version":"10.15.7","device_id":"9ad348ab5dbd7acbebdcb8b7bfe7030d","device_type":"computer"}}}

  res = requests.post(token, headers = headers, json = payload)
  res = res.json()
  client_token = res['granted_token']['token']
  return client_token

def getPlaylistHeaders(playlistId, client_token, bearer_token):
  headersx = headers = {
      "authority": "api-partner.spotify.com",
      "method": "GET",
      "scheme": "https",
      "accept": "application/json",
      "accept-encoding": "gzip, deflate, br, zstd",
      "accept-language": "en",
      "app-platform": "WebPlayer",
      "cache-control": "no-cache",
      "content-type": "application/json;charset=UTF-8",
      "origin": "https://open.spotify.com",
      "pragma": "no-cache",
      "priority": "u=1, i",
      "referer": "https://open.spotify.com/",
      "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
      "sec-ch-ua-mobile": "?0",
      "sec-ch-ua-platform": '"macOS"',
      "sec-fetch-dest": "empty",
      "sec-fetch-mode": "cors",
      "sec-fetch-site": "same-site",
      "spotify-app-version": "1.2.44.216.g1fe6e17d",
      "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
  }
  headers["path"] = f"/pathfinder/v1/query?operationName=fetchPlaylist&variables=%7B%22uri%22%3A%22spotify%3Aplaylist%3A{playlistId}%22%2C%22offset%22%3A0%2C%22limit%22%3A25%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22a4712aae8c695640d6e6408472a10d1e40d3a09ec862cf690bd2adb4ae84e1ee%22%7D%7D"
  headersx['client-token'] = client_token
  headersx['authorization'] = bearer_token

  return headers

def getPlayListData(playlistId, playHeaders):
  play_api = f"https://api-partner.spotify.com/pathfinder/v1/query?operationName=fetchPlaylist&variables=%7B%22uri%22%3A%22spotify%3Aplaylist%3A{playlistId}%22%2C%22offset%22%3A0%2C%22limit%22%3A25%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22a4712aae8c695640d6e6408472a10d1e40d3a09ec862cf690bd2adb4ae84e1ee%22%7D%7D"
  response = requests.get(play_api, headers = playHeaders)
  response = response.json()
  return response

def extract_track_details(data):
  track_details = []
  items = data["data"]["playlistV2"]["content"]["items"]

  for item in items:
      track_data = item["itemV2"]["data"]
      track_name = track_data["name"]
      track_primary_artist = track_data['artists']['items'][0]['profile']['name']
      track_uri = track_data["uri"]
      track_duration_ms = track_data["trackDuration"]["totalMilliseconds"]


      track_details.append({
          "track_name": track_name,
          "track_uri": track_uri,
          "track_duration_ms": track_duration_ms,
          "track_Ist_artist" : track_primary_artist
      })
  return track_details

def queryFunc(query, slowFlag):
    res = Search(query).results
    print(res)
    
    try:
        searchRes = [
            {
                "title": itm.title,
                "length": itm.length,
                "url": itm.watch_url,
                "views": itm.views,
                "author": itm.author,
                "embed_code": f'''<iframe src="{itm.embed_url}"></iframe>'''
            }
            for itm in res
        ]
    except Exception as e:
        print("error in search")
        raise gr.Error("Error occured in pytube")

    slowRegex = re.compile(r'\bslowed\b', re.IGNORECASE)
    mashupRegex = re.compile(r'\sx\s', re.IGNORECASE)
    longVerRegex = re.compile(r'\bhour\b', re.IGNORECASE)
    

    if slowFlag == 'slowed':
        filteredTracks = [
            itm for itm in searchRes
            if not mashupRegex.search(itm['title'])
            and not ("mashup" in itm['title'].lower())
            and not longVerRegex.search(itm['title'])
            and slowRegex.search(itm['title'].lower())
        ]
        filteredTracks = sorted(filteredTracks, key=lambda x: x['views'], reverse=True)
        filteredTracks = filteredTracks[:3]
        filteredTracks = sorted(filteredTracks, key=lambda x: x['length'], reverse=True)
    
    else:
        filteredTracks = [
            itm for itm in searchRes
            if not mashupRegex.search(itm['title'])
            and not ("mashup" in itm['title'].lower())
            and not longVerRegex.search(itm['title'])
        ]
        filteredTracks = sorted(filteredTracks, key=lambda x: x['views'], reverse=True)
        filteredTracks = filteredTracks[:3]

    if filteredTracks:
        return filteredTracks[0]
    return None

def download_video(url, output_path):
    yt = YouTube(url)
    stream = yt.streams.get_highest_resolution()
    print(f"Downloading: {yt.title}")
    stream.download(output_path=output_path)
    print(f"Finished downloading: {yt.title}")

def zip_folder(folder_path, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zipf.write(file_path, arcname)

async def async_download_video(url, output_path, executor):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, download_video, url, output_path)


def extract_audio(video_path, audio_path):
    # Define the FFmpeg command
    command = [
        'ffmpeg',         # The FFmpeg executable
        '-i', video_path, # Input file path
        '-q:a', '0',      # Set audio quality (0 is best)
        '-map', 'a',      # Select the audio stream
        audio_path        # Output file path
    ]
    
    try:
        # Run the FFmpeg command
        subprocess.run(command, check=True)
        print(f"Extracted audio from {video_path} to {audio_path}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def process_playlist(purl, search = None):

    if "playlist" not in purl.lower().split('/'):
      raise gr.Error("Not a valid PLAYLIST link, make sure there's a 'playlist' in the link")

    headers = getHeaders()
    client_id, correlation_id, bearer_token, playlistId = authStuff(purl, headers)
    print(playlistId)
    client_token = clientToken(client_id, headers)
    playHeaders = getPlaylistHeaders(playlistId, client_token, bearer_token)
    data = getPlayListData(playlistId, playHeaders)
    tracks = extract_track_details(data)

    slowFlag = None
    if search:
       slowFlag = 'slowed'
       print(search)
       queries = [f"{itm['track_name']} {itm['track_Ist_artist']} {search} " for itm in tracks]
    else:
       queries = [f"{itm['track_name']} {itm['track_Ist_artist']}" for itm in tracks]

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [loop.run_in_executor(executor, queryFunc, query, slowFlag) for query in queries]
        topSongs = loop.run_until_complete(asyncio.gather(*tasks))

    urls = [itm['url'] for itm in topSongs if itm]
    download_dir = './downloads'

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    with ThreadPoolExecutor() as executor:
        tasks = [async_download_video(url, download_dir, executor) for url in urls]
        loop.run_until_complete(asyncio.gather(*tasks))

    video_paths = [os.path.join(download_dir, f) for f in os.listdir(download_dir) if os.path.isfile(os.path.join(download_dir, f))]
    audio_output_dir = './audio_files'

    if not os.path.exists(audio_output_dir):
        os.makedirs(audio_output_dir)

    for video_path in video_paths:
        audio_file = os.path.splitext(os.path.basename(video_path))[0] + '.mp3'
        audio_path = os.path.join(audio_output_dir, audio_file)
        extract_audio(video_path, audio_path)

    folder_path = './audio_files'
    output_filename = 'audio.zip'
    zip_folder(folder_path, output_filename)
    
    video_folder = './downloads'
    videoZip = 'video.zip'
    zip_folder(video_folder, videoZip)
    print("Files zipped successfully")
    return [output_filename, videoZip]

def freeMem():
    dirs_to_delete = ['audio_files', 'downloads']
    files_to_delete = ['audio.zip', 'video.zip']

    for directory in dirs_to_delete:
        if os.path.exists(directory):
            shutil.rmtree(directory)
            print(f"Deleted directory: {directory}")

    for f in files_to_delete:
      if os.path.exists(f):
          os.remove(f)
          print(f"Deleted file: {f}")


def gradio_app(purl, version):
    freeMem()
    zip_file = process_playlist(purl, version)
    return zip_file


with gr.Blocks(title = "SpotifyMp3Downloader") as demo:
  gr.Markdown("SPOTIFY->MP3 DOWNLOADER")

  with gr.Row():

    with gr.Column():
      playlistUrl = gr.Textbox(label = "ENTER PLAYLIST URL")
      version = gr.Dropdown(['slowed', 'slowed and reverbed', 'spedup'], interactive = True)
      with gr.Row():
        submitButton = gr.Button(value = "Submit", variant = "primary")
        gr.ClearButton(components = [playlistUrl, version])

    with gr.Column():
      output = gr.Files(label = "Download zip files", interactive = False)

    submitButton.click(fn = gradio_app, inputs = [playlistUrl, version], outputs = [output])

app = gr.mount_gradio_app(app, demo, path = '/')

if __name__ == '__main__':
    app.run()
