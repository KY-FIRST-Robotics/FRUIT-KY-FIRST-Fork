import json         # response handling
import requests     # API data request
import base64       # API hashing
import datetime     # str conversion

translateSymbol = {'M': 'Playoffs', 'Q': 'Quals', 'F': 'Finals'}

# CREDENTIALS (dict): credentials from https://frc-events.firstinspires.org/services/api, contains "FRC_username" and "FRC_key" entries
with open("CREDENTIALS", "r") as file:
    CREDENTIALS = json.load(file) # contains username + authKey

def prepareHeadersFMS(username, authKey):
    """Prepares request header for FMS, allows for authentication

    Args:
        username (str): username for frc-events.firstinspires.or or ftc-events.firstinspires.org
        authKey (str): authKey provided from related service

    Returns:
        headers (dict): header for use in requests.get for FMS

    """
    AuthorizationToken = (username+':'+authKey).encode("ascii")
    Authorization = base64.b64encode(AuthorizationToken).decode("ascii")

    headers = {'Authorization': 'Basic '+Authorization}

    return headers

def getMatchesFromFMS(year:int, eventCode:str):
    """Connects to FRC FMS records for an event and stores them

    Args:
        year (int): season year
        eventCode (str): event code

    Returns:
        matches (dict): {'X0': {start': datetime.datetime, 'post': datetime.datetime, 'teamsRed': list(int), 'teamsBlue': list(int)]}

    """

    # define API url and request headers, based on: https://frc-api-docs.firstinspires.org/#733f4607-ab40-4e00-b3e1-36cfb1a2e77e
    url = 'https://frc-api.firstinspires.org/v3.0/'+str(year)+'/matches/'+eventCode
    headers = prepareHeadersFMS(CREDENTIALS['FRC_username'], CREDENTIALS['FRC_key'])

    # make the API call
    responseQuals = requests.get(url+'?tournamentLevel=Qualification', headers=headers, verify=False)
    responsePlayoffs = requests.get(url+'?tournamentLevel=Playoff', headers=headers, verify=False)

    # extract the match ID, start time, post time
    matches = rewrapMatches(responseQuals.json()['Matches'], 'Q')

    matchesPlayoffs = rewrapMatches(responsePlayoffs.json()['Matches'], 'M')
    matches.update(matchesPlayoffs)

    matchesFinals = rewrapMatches(responsePlayoffs.json()['Matches'], 'F', len(matchesPlayoffs.keys()))
    matches.update(matchesFinals)

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

def rewrapMatches(matchesFMS, matchChar:str, offset=0):
    """Reformats FRC FMS response into a dict of matches

    Args:
        isQuals (bool): are the matches qualifications?

    Returns:
        dict: match information and times in datetime.datetime
    
    ToDo:
        * Combine with rewrapMatchesFTC

    """
    return {match['description'][0]+str(match['matchNumber']-offset):  
        {'start':str2dte(match['actualStartTime']), 'post':str2dte(match['postResultTime']),
        'teamsRed': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='R'],
        'teamsBlue': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='B']} 
        for match in matchesFMS if (match['description'][0] == matchChar)*(match['actualStartTime'] != None)*(match['postResultTime'] != None)}

def rewrapMatchesFTC(matchesFMS, isQuals=True):
    """Reformats FTC FMS response into a dict of matches

    Args:
        isQuals (bool): are the matches qualifications?

    Returns:
        dict: match information and times in datetime.datetime

    """
    if isQuals:
        return {match['tournamentLevel'][0]+str(match['matchNumber']):  
            {'start':str2dte(match['actualStartTime']), 'post':str2dte(match['postResultTime']),
            'teamsRed': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='R'],
            'teamsBlue': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='B']} 
            for match in matchesFMS if (match['actualStartTime'] != None)*(match['postResultTime'] != None)}
    else:
        return {match['tournamentLevel'][0]+str(match['series']):  
            {'start':str2dte(match['actualStartTime']), 'post':str2dte(match['postResultTime']),
            'teamsRed': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='R'],
            'teamsBlue': [team['teamNumber'] for team in match['teams'] if team['station'][0]=='B']} 
            for match in matchesFMS if (match['actualStartTime'] != None)*(match['postResultTime'] != None)}


def getMatchesForFTC(year:int, eventCode:str, username:str, authKey:str):
    """Connects to FTC FMS records for an event and stores them

    Args:
        year (int): season year
        eventCode (str): event code
        username (str): username for ftc-events.firstinspires.org
        authKey (str): authKey provided from related service

    Returns:
        matches (dict): {'X0': {start': datetime.datetime, 'post': datetime.datetime, 'teamsRed': list(int), 'teamsBlue': list(int)]}

    """
    # define API url and request headers, based on: https://frc-api-docs.firstinspires.org/#733f4607-ab40-4e00-b3e1-36cfb1a2e77e
    url = 'http://ftc-api.firstinspires.org/v2.0/'+str(year)+'/matches/'+eventCode
    headers = prepareHeadersFMS(username, authKey)

    # make the API call
    responseQuals = requests.get(url+'?tournamentLevel=Qualification', headers=headers)
    responsePlayoffs = requests.get(url+'?tournamentLevel=Playoff', headers=headers)

    # extract the match ID, start time, post time
    matches = rewrapMatchesFTC(responseQuals.json()['matches'], True)

    matchesPlayoffs = rewrapMatchesFTC(responsePlayoffs.json()['matches'], False)
    matches.update(matchesPlayoffs)

    # sort by start time
    matches = {k: v for k, v in sorted(matches.items(), key=lambda item: item[1]['start'])}

    return matches

def livestreamDescription(matches:dict, originMin:int, originSec:int,  originMatchID:str = 'Q1'):
    """Generates a string that can be placed in the description of a YouTube livestream recording to provide timestamps for matches

    Args:
        matches (dict): match info dictionary
        originMin (int): start time of origin match (minutes part)
        originSec (int): start time of origin match (seconds part)
        originMatchID (str): origin match string identifier

    Returns:
        str : youtube session
    """
    desc = '== Matches ==\n'

    start = datetime.timedelta(minutes=originMin, seconds=originSec-3)

    try:
        matches[originMatchID]['start']
    except KeyError:
        raise KeyError('match ID does not exist')

    for matchID, matchInfo in matches.items():
        desc += str(matchInfo['start'] - matches[originMatchID]['start'] + start).split(".")[0] + " " + matchID + "\n"

    print(desc)
    
    return desc