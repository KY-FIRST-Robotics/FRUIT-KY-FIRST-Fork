import requests


def get_youtube_auth(api_key:str):
    api_key = "AIzaSyAHHdkKDLSpsicELAan30eVsym4L20ypQQ"
    return api_key

def convertID2Username(api_key:str, channel_id:str):
    response = requests.get(
    "https://www.googleapis.com/youtube/v3/channels",
    params={
    "key": api_key,
    "id": channel_id,
    "part": "id"
    
    
        },
    )
    return response.json()["items"][0]["id"]

# def main():
#     get_youtube_auth("AIzaSyAHHdkKDLSpsicELAan30eVsym4L20ypQQ")

# main()