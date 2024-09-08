import json         # response handling
import requests     # API data request
import base64       # API hashing
import datetime     # str conversion

translateSymbol = {'M': 'Playoffs', 'Q': 'Quals', 'F': 'Finals'}

# AUTHENTICATION (dict): credentials from https://frc-events.firstinspires.org/services/api, contains "username" and "authToken"
with open("AUTHENTICATION", "r") as file:
    AUTHENTICATION = json.load(file) # contains username + authToken

def getMatchesFromFMS(year:int, eventCode:str):
    """Connects to FMS records for an event and stores them

    Args:
        year (int): season year
        eventCode (str): event code

    Returns:
        timeObject (datetime.datetime)

    """
    AuthorizationKey = (AUTHENTICATION['username']+':'+AUTHENTICATION['authToken']).encode("ascii")
    Authorization = base64.b64encode(AuthorizationKey).decode("ascii")

    # define API url and request headers, based on: https://frc-api-docs.firstinspires.org/#733f4607-ab40-4e00-b3e1-36cfb1a2e77e
    url = 'https://frc-api.firstinspires.org/v3.0/'+str(year)+'/matches/'+eventCode
    headers = {'Authorization': 'Basic '+Authorization}

    # make the API call
    responseQuals = requests.get(url+'?tournamentLevel=Qualification', headers=headers, verify=False)
    responsePlayoffs = requests.get(url+'?tournamentLevel=Playoff', headers=headers, verify=False)

    # combine API results
    matchesRaw = (responseQuals.json()['Matches'] + responsePlayoffs.json()['Matches'])

    # extract the match ID, start time, post time
    matches = {match['description'][0]+str(match['matchNumber']):  
        {'start':str2dte(match['actualStartTime']), 'post':str2dte(match['postResultTime']),
        'teamsRed': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='R'],
        'teamsBlue': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='B']} 
        for match in matchesRaw if (match['description'][0] in translateSymbol.keys())*(match['actualStartTime'] != None)*(match['postResultTime'] != None)}

    # sort by start time
    matches = {k: v for k, v in sorted(matches.items(), key=lambda item: item[1]['start'])}

    return matches

# sometimes milliseconds isn't reported in FMS - use this to fix that
def str2dte(timeString):
    """Converts datetime string that may contain decimal seconds

    Args:
        timeString (str): string of format %Y-%m-%dT%H:%M:%S(.%f)

    Returns:
        timeObject (datetime.datetime)

    """
    try:
        timeObject = datetime.datetime.strptime(timeString, "%Y-%m-%dT%H:%M:%S.%f")
    except ValueError:
        timeObject = datetime.datetime.strptime(timeString, "%Y-%m-%dT%H:%M:%S")
    
    return timeObject