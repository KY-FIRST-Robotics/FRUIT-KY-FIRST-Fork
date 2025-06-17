import requests
import os
import subprocess
import streamlink


def getYoutubeAuthHeader(client_id:str, client_secret:str, refresh_token:str):
    """
    Retrieves the access token for the Youtube API.

    Args:
        client_id (str): Your Youtube client ID.
        client_secret (str): Your Youtube client secret.

    Returns:
        dict: header for use in requests.get for Youtube
    
    Raises:
      Exception: Unable to obtain Youtube access token
    """
    
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token',
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "redirect_uris": ["http://localhost"]
       
    }
    
    response = requests.post("https://oauth2.googleapis.com/token", data=params)

    if response.status_code == 200:
        return {'Client-ID': client_id, 'Authorization': f'Bearer {response.json()['access_token']}'}
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")

def getYoutubeVideoData(client_id:str, client_secret:str, vod_id:int):
    """
    Retrieves the access token for the Youtube API.

    Args:
        client_id (str): Your Youtube client ID.
        client_secret (str): Your Youtube client secret.
        vod_id (int): Youtube VOD ID

    Returns:
        dict: information about the video
    """

    # obtain data about VOD
    headersYoutubeAPI = getYoutubeAuthHeader(client_id, client_secret)
    response = requests.get('https://www.googleapis.com/youtube/v3/videos'+str(vod_id), headers=headersYoutubeAPI)

    return response.json()['data'][0]

def convertID2Username(client_id:str, client_secret:str, username:int):
    """
    Retrieves the associated user ID provided a Youtube username

    Args:
        client_id (str): Your Youtube client ID.
        client_secret (str): Your Youtube client secret.
        username (str): Youtube username

    Returns:
        user_id (str): Youtube user ID
    """
        
    headersYoutubeAPI = getYoutubeAuthHeader(client_id, client_secret)
    user_response = requests.get('https://www.googleapis.com/youtube/v3/channels'+username, headers=headersYoutubeAPI)
    user_data = user_response.json()
    user_id = user_data['data'][0]['id']

    return user_id

def getLatestYoutubeVODs(client_id:str, client_secret:str, user_id:str):
    """
    Retrieves the associated user ID provided a Youtube username

    Args:
        client_id (str): Your Youtube client ID.
        client_secret (str): Your Youtube client secret.
        user_id (str): Youtube user ID

    Returns:
        vods_data (list): list of VOD information
    """
        
    headersYoutubeAPI = getYoutubeAuthHeader(client_id, client_secret)
    vods_url = f'https://www.googleapis.com/youtube/v3/videos{user_id}'
    vods_response = requests.get(vods_url, headers=headersYoutubeAPI)
    vods_data = vods_response.json()['data']

    return vods_data

def downloadYoutubeClip(vod_id: int, startTimestamp: str, durationSeconds: str, outputFileName: str):
    """
    Downloads a clip of a Youtube VOD, be wary of weird timestamps
        * VODs are broken into 10 second segments (m3u8 process)
        * segments are from XX:X1 to XX:X1 + 9.999 but return XX:XX to XX:XX + 10 ¯\_(ツ)_/¯

    Args:
        vod_id (int): Youtube VOD ID
        startTimestamp (str): timestamp to start at (XX:XX)
        durationSeconds (str): duration (XX:XX)
        outputFileName (str): location & name of output filepath

    """
    # delete file if it already exists
    try:
        os.remove(outputFileName)
    except OSError:
        pass
    
    # prepare command
    command = [
        'streamlink',
        "https://www.youtube.com/watch?v="+str(vod_id),
        'best',
        '--hls-start-offset', startTimestamp,
        '--hls-duration', durationSeconds,
        '-o', outputFileName,
        '--hls-live-edge', '1'
    ]
    
    # run command in terminal
    subprocess.run(command)

def durationStr2Sec(duration):
    """
    translates duration in string format to integer

    Args:
        duration (str): duration in XhXXmXXs format

    Returns:
        total_seconds (int): duration in seconds
    """

    # Initialize total seconds to 0
    total_seconds = 0
    
    # Split the duration into parts based on 'h', 'm', and 's'
    if 'h' in duration:
        hours, duration = duration.split('h')
        total_seconds += int(hours) * 3600
    if 'm' in duration:
        minutes, duration = duration.split('m')
        total_seconds += int(minutes) * 60
    if 's' in duration:
        seconds = duration.split('s')[0]
        total_seconds += int(seconds)

    return total_seconds