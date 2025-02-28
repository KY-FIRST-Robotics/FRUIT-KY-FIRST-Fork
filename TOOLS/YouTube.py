import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http

def authenticate_youtube(SCOPES: list=["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]):
    """Authenticates a session with YouTube using oauth

    Args:
        SCOPES (list): YouTube Data api scopes 

    Returns:
        youtube : youtube session
    """

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
    flow.redirect_uri = 'http://localhost:8080/'

    credentials = flow.run_local_server(port=8080)

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

    return youtube

def upload_video(youtube, media_file:str, request_body:dict, thumbnail: str=None, playlistID:str=''):
    """Uploads a video to YouTube; uses 1700 quota (1600 upload + 50 thumbnail + 50 playlist)

    Args:
        youtube : youtube session
        media_file (str): path to video file
        request_body (dict): document following YouTube format for upload
        thumbnail (str): path to thumbnail file
        playlistID (str): YouTube playlist ID to add video to (everything after https://www.youtube.com/playlist?list=)

    Returns:
        responseID : successfully uploaded YouTube video ID
    """

    # Upload the video
    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=googleapiclient.http.MediaFileUpload(media_file, chunksize=-1, resumable=True)
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    
    if thumbnail != None:
        request = youtube.thumbnails().set(
            videoId=response['id'],
            media_body=googleapiclient.http.MediaFileUpload(thumbnail)
        )
        response_thumbnail = request.execute()
    
    if playlistID != '':
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlistID,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": response['id']
                    }
                }
            }
        )
        response_playlist = request.execute()
    
    return response['id']

def formatYouTubeTitle(matchID:str, event_title:str, year:int, replay:bool=False):
    """
    Provide a human-readable title for match video on YouTube
        * Quals 41 | 2024 FIN Tippecanoe District

    Args:
        matchID (str): match ID
        event_title (str): event title
        year (int): match year
        replay (bool): video is a replay of a previous match
    
    Returns:
        title (str): matches not found in log file

    """

    translateSymbol = {'M': 'Playoffs', 'P': 'Playoffs', 'Q': 'Quals', 'F': 'Finals'}

    if replay:
        return f"{translateSymbol[matchID[0]]} {matchID[1:]}R | {year} {event_title}"
    else:
        return f"{translateSymbol[matchID[0]]} {matchID[1:]} | {year} {event_title}"