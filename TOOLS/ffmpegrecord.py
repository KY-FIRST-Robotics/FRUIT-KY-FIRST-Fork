import subprocess
import time
import requests
import json
from datetime import datetime
import threading
import subprocess

with open("CREDENTIALS", "r") as file:
    CREDENTIALS = json.load(file)
CHANNEL_ID = CREDENTIALS["Youtube_Channel_ID"]
API_KEY = CREDENTIALS["Youtube_API_Key"]
CHECK_INTERVAL = 10  # seconds

ffmpeg_process = None


def get_live_video_url(channel_id, api_key):
    url = (
        f"https://www.googleapis.com/youtube/v3/search?"
        f"part=snippet&channelId={channel_id}&eventType=live&type=video&key={api_key}"
    )
    response = requests.get(url)
    data = response.json()
    items = data.get("items", [])
    if items:
        video_id = items[0]["id"]["videoId"]
        return f"https://www.youtube.com/watch?v={video_id}"
    return None


def resolve_stream_url(youtube_url):
    # This calls yt-dlp to extract the direct stream URL, as opposed to the public livestream URL
    result = subprocess.run(
        ["yt-dlp", "-g", "-f", "best", youtube_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    else:
        print("[ERROR] yt-dlp failed:", result.stderr)
        return None


def generate_output_filename():
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )  # Timestamps recordings to avoid overwriting the same file
    return f"TOOLS/recordings/{timestamp}.mp4"


def record_stream(stream_url, output_file):
    global ffmpeg_process
    cmd = ["ffmpeg", "-y", "-i", stream_url, "-c", "copy", "-f", "mpegts", output_file]
    print(f"[INFO] Starting recording to: {output_file}")
    ffmpeg_process = subprocess.Popen(
        cmd
    )  # Starts global process so stop_recording can terminate recording


def start_recording():
    """
    Runs ffmpeg recording in a thread to prevent GUI from freezing
    """
    thread = threading.Thread(target=run_recording_process, daemon=True)
    thread.start()


def stop_recording():

    global ffmpeg_process
    if ffmpeg_process:
        ffmpeg_process.terminate()
        ffmpeg_process.wait()
        ffmpeg_process = None


def main():
    print("[INFO] Checking for stream...")
    while True:
        live_url = get_live_video_url(CHANNEL_ID, API_KEY)
        if live_url:
            print(f"[INFO] Stream live at: {live_url}")
            stream_url = resolve_stream_url(live_url)
            if stream_url:
                output_file = generate_output_filename()
                record_stream(stream_url, output_file)
            else:
                print("[ERROR] Could not resolve stream URL.")
            break
        else:
            print("[INFO] Stream not live yet. Checking again in 10 seconds...")
            time.sleep(CHECK_INTERVAL)


# Wrapper function for GUI use
def run_recording_process():
    main()
