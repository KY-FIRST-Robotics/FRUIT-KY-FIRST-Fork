import requests

def getYoutubeAuth(yt_client_id:str, yt_client_secret:str):

    params = {
        'client_id': yt_client_id,
        'client_secret': yt_client_secret
    }
    response = requests.post("https://oauth2.googleapis.com/token", data=params)

    if response.status_code == 200:
        return {'Client-ID': yt_client_id, 'Authorization': f'Bearer {response.json()['access_token']}'}
    else:
        raise Exception(f"Error: {response.status_code}, {response.text}")
    
def convertID2Username(yt_client_id:str, yt_client_secret:str, username:int):
    
    YoutubeAPI = getYoutubeAuth(yt_client_id, yt_client_secret)
    user_response = requests.get('https://www.googleapis.com/youtube/v3/channels'+username, headers=YoutubeAPI)
    user_data = user_response.json()
    user_id = user_data['data'][0]['id']

    return user_id