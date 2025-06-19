import time
import datetime
from obswebsocket import obsws, requests
from googleapiclient.discovery import build

Youtube_API_key = "AIzaSyBSI7ifUNm2Q6Nzi3ThLY4sQWjx7-mC9q8"
Youtube_Channel_ID = "UCbRpsLis1c4zvg3jkjBDMLg"
OBS_Host = "localhost"
OBS_Port = 4455
OBS_Web_Socket_Password = ""
pollInterval = 10

def is_stream_live(youtube, channel_id):
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        type="video",
        eventType="live",
        maxResults=1
    )
    response = request.execute()
    return len(response.get("items", [])) > 0

def start_obs_recording(host, port, password):
    try:
        ws = obsws(host, port, password)
        ws.connect()
        print(f"[{datetime.datetime.now()}] Connected to OBS.")

        ws.call(requests.StartRecord())
        print(f"[{datetime.datetime.now()}] Recording started.")

        ws.disconnect()
    except Exception as e:
        print(f"[ERROR] Failed to start OBS recording: {e}")

def main():
    youtube = build("youtube", "v3", developerKey=Youtube_API_key)
    recording_started = False

    print(f"[INFO] Watching for stream on channel: {Youtube_Channel_ID}")
    while not recording_started:
        try:
            if is_stream_live(youtube, Youtube_Channel_ID):
                print(f"[{datetime.datetime.now()}] 🚨 Stream is live!")
                start_obs_recording(OBS_Host, OBS_Port, OBS_Web_Socket_Password)
                recording_started = True
            else:
                print(f"[{datetime.datetime.now()}] Not live yet. Retrying...")
        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(pollInterval)

if __name__ == "__main__":
    main()
