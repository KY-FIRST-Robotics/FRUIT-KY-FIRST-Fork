import json #credentials load
import datetime #date and str manipulation
import math #ceil function for twitch segments
import threading #allows for multiple things to occur at once
import queue #queue process for SEEK, BUILD, SEND
import time #time.sleep used for waiting
import os #creating directories
import sys 

# libraries for GUI
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QLabel, QHBoxLayout, QComboBox

# libraries for video chopping
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.audio.fx.all import audio_fadeout, audio_fadein

# custom functions
from TOOLS.CredentialsPopUp import CredDialog
from TOOLS.YouTube import authenticate_youtube
from TOOLS.Twitch import covertID2Username
from TOOLS.FMS import getMatchesForFTC
from TOOLS.Twitch import getLatestTwitchVODs
from TOOLS.Twitch import durationStr2Sec
from TOOLS.Twitch import downloadTwitchClip
from TOOLS.YouTube import upload_video
from TOOLS.TBA import postTheBlueAlliance
from TOOLS.TBA import translateMatchString

# create directories if missing
os.makedirs('log/', exist_ok=True)
os.makedirs('output/', exist_ok=True)

class Worker(QObject):
    progress_signal_1 = pyqtSignal(int)
    progress_signal_2 = pyqtSignal(int)
    progress_signal_3 = pyqtSignal(int)

    def __init__(self, user_data, stop_event):
        super().__init__()
        self.user_data = user_data
        self.stop_event = stop_event

    def make_sauce(self):
        with open('log/send.txt', 'r') as file:
            count_finished = len([line for line in file if self.user_data['event_code'] in line])
        
        self.count_seen = count_finished
        self.count_built = count_finished
        self.count_sent = count_finished

        self.progress_signal_1.emit(count_finished)
        self.progress_signal_2.emit(count_finished)
        self.progress_signal_3.emit(count_finished)

        # load API credentials
        with open("CREDENTIALS", "r") as file:
            CREDENTIALS = json.load(file)

        # start a YouTube session (complete in browser)
        YouTube_Session = authenticate_youtube()

        # get numeric Twitch user ID given str username
        twitch_user_id = covertID2Username(CREDENTIALS['Twitch_clientID'], CREDENTIALS['Twitch_clientSecret'], self.user_data['twitch_user'])

        # determine local timezone
        device_timezone = datetime.datetime.now().astimezone().tzinfo

        def match2str(match):
            """
            Formats a file-name-safe string that is unique for a match

            Args:
                match (dict): {'id': X00, 'start':datetime.datetime, 'post':...}
            
            Returns:
                str

            """
            return f"{self.user_data['event_code']}_{match['id']}_{match['start'].hour:02}{match['start'].minute:02}"


        def listNotInLog(logPath:str, matches:list):
            """
            Return matches where their related match2str was not found in log file

            Args:
                logPath (str): path and name of log file
                matches (list): contains match data dictionaries
            
            Returns:
                list: matches not found in log file

            """

            # Open the file and save lines to list
            with open(logPath, 'r') as file:
                lines_list = [line.strip() for line in file]
            
            # Return matches that do not appear
            return [match for match in matches if not(match2str(match) in lines_list)]

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

        # Clear and entries in send log file that were not finished
        with open('log/send.txt', 'r') as source_file, open('log/seek.txt', 'w') as destination_file:
            # Read the contents of the source file and write them to the destination file
            destination_file.write(source_file.read())

        # Create the queues
        queueBuild = queue.Queue()
        queueSend = queue.Queue()

        def watch(twitch_user_id, latestVODs):
            """look out for new videos on the twitch"""
            if self.stop_event.is_set():
                return
            
            # get the latest VODs for a user ID (pagination ignored)
            new_VODs = getLatestTwitchVODs(CREDENTIALS['Twitch_clientID'], CREDENTIALS['Twitch_clientSecret'], twitch_user_id)

            # covert information into more useable form
            for vod in new_VODs:
                created_at_datetime = datetime.datetime.fromisoformat(vod['created_at'])
                vod['created_at'] =  created_at_datetime.astimezone(device_timezone).replace(tzinfo=None)
                vod['duration'] = durationStr2Sec(vod['duration'])
            
            newIDs = [vod['id'] for vod in new_VODs if not(vod['id'] in [vod_old['id'] for vod_old in latestVODs])]
            if newIDs:
                print('New VODs!', newIDs)
            
            # Clear the existing VODs and append all new VODs to the shared list
            latestVODs.clear()
            latestVODs.extend(new_VODs)
            
            # Schedule the function to run again after 15 minutes
            threading.Timer(15*60, watch, args=(twitch_user_id, latestVODs)).start()

        # Schedule the function to start looking
        latestVODs = []
        watch(twitch_user_id, latestVODs)

        def seek():
            """seek thread that adds items to the first queue every minute."""
            while not self.stop_event.is_set():
                # obtain match information from FMS
                if self.user_data['program'] == 'FRC':
                    raise SystemError('I have not built this yet!')
                elif self.user_data['program'] == 'FTC':
                    matches = getMatchesForFTC(self.user_data['event_year'], self.user_data['event_code'], CREDENTIALS['FRC_username'], CREDENTIALS['FRC_key'])
                
                # reformat into list and remove ones that are too fresh
                matches_list = [{'id': k} | v for k,v in matches.items() if (datetime.datetime.now() - v['post']).total_seconds() >= 50]

                # determine which matches have not already been processed
                matches_new = listNotInLog('log/seek.txt', matches_list)

                # sent matches to builder to be generated, add them to log and count
                with open('log/seek.txt', 'a') as file:
                    for match in matches_new:
                        match_str = match2str(match)
                        print('SEEK: '+match_str)
                        queueBuild.put(match)
                        file.write(match_str+"\n")
                        self.count_seen += 1
                        self.progress_signal_1.emit(self.count_seen)

                # wait a little bit before looking for new matches
                time.sleep(100)

        def build():
            """Thread that moves items from the first queue to the second queue after 25 seconds."""
            while not self.stop_event.is_set():
                # if there are no Twitch stream VODs, wait a minute
                if not latestVODs:
                    print('no VODs!')
                    time.sleep(60)
                    continue

                try:
                    # grab a match from the build queue, try for 30 seconds then timeout
                    match = queueBuild.get(timeout=30)

                    # determine which VOD contains the match
                    for vod in reversed(latestVODs):
                        startInVideo = (match['start'] - vod['created_at']).total_seconds() < vod['duration']
                        endInVideo = (match['post'] - vod['created_at']).total_seconds() < vod['duration']

                        # video is in the same VOD
                        if startInVideo and endInVideo:
                            break
                        
                        # video is in different VODs (XOR)
                        if startInVideo ^ endInVideo:
                            print('bad times ahead')

                        # default exit is latest VOD

                    # double check VOD and match are on the same day (prevents stale)
                    if (match['start'] - vod['created_at']).total_seconds() > (24*60*60):
                        print('ope!')
                    
                    # prepare VOD cut start-point
                    startSeconds = ((match['start'] - vod['created_at']).total_seconds() +3 -3) #add delay & subtract countdown
                    trim = startSeconds % 10
                    if trim > 9:
                        startSegment = ((math.ceil(startSeconds)//10)-1)*10
                    else:
                        startSegment = (math.ceil(startSeconds)//10)*10
                    
                    # prepare VOD clip duration
                    durationSeconds = ((match['post'] - match['start']).total_seconds() + 13.9 + self.user_data['post_reveal'])
                    duration = str(datetime.timedelta(seconds=((durationSeconds // 10)+2)*10))

                    # get clip from Twitch that contains both match + its score
                    downloadTwitchClip(int(vod['id']), str(datetime.timedelta(seconds=(startSegment))), duration, 'output/temp.mp4')

                    try:
                        with VideoFileClip('output/temp.mp4') as video:

                            # clip the match and the scores, adding audio fades to taste
                            seg_match = audio_fadein(video.subclip(trim, trim + self.user_data['match_length']), 0.5)
                            seg_score = audio_fadeout(video.subclip(trim + durationSeconds - 13.9, trim+durationSeconds), 2)

                            # merge together match and scores
                            final = concatenate_videoclips([seg_match, seg_score])

                            # save the results as a file
                            final.write_videofile('output/'+match2str(match)+'.mp4', audio_codec='aac')
                        
                        queueSend.put(match)
                        print("BUILT: "+match2str(match))
                        self.count_built += 1
                        self.progress_signal_2.emit(self.count_built)
                    except ValueError as errorText:
                        print(f'AAAHHHHHHH {errorText}')
                        queueBuild.put(match)
                    
                except queue.Empty:
                    continue

        def send():
            """send thread that releases items from the second queue after 10 seconds."""
            while not self.stop_event.is_set():
                try:
                    match = queueSend.get(timeout=30)

                    title = formatYouTubeTitle(match["id"], self.user_data['event_title'], self.user_data['event_year']) #FMS doesn't report replay?
                    
                    request_body = {
                        "snippet": {
                            "title": title,
                            "description": "Footage of this event is courtesy of FIRST Indiana Robotics.\n\nFollow us on Twitter (@FIRSTINRobotics), Facebook (FIRST Indiana Robotics), and Twitch (FIRSTINRobotics).\n\nFor more information and future event schedules, visit our website: https://www.firstindianarobotics.org",
                            "categoryId": "28",  # Category ID for "Science & Technology"
                            "tags": [match["id"], self.user_data['program'], "trimFRC_BCC"]
                        },
                        "status": {
                            "privacyStatus": "unlisted"
                        }
                    }

                    videoID = upload_video(YouTube_Session, 'output/'+match2str(match)+'.mp4', request_body, None, self.user_data['playlist_ID'])

                    if self.user_data['program'] == 'FRC':
                        data = {translateMatchString(match["id"]): videoID}
                        #response_TBA = postTheBlueAlliance(CONFIG['TBA']['Auth_Id'], CONFIG['TBA']['Auth_Secret'], CONFIG['TBA']['eventKey'], data)
                    
                    with open('log/send.txt', 'a') as file:
                        file.write(match2str(match)+"\n")
                    
                    print("SENT: "+match2str(match))
                    self.count_sent += 1
                    self.progress_signal_3.emit(self.count_sent)
                except queue.Empty:
                    continue

        # Create threads
        seek_thread = threading.Thread(target=seek)
        build_thread = threading.Thread(target=build)
        send_thread = threading.Thread(target=send)

        # Start threads
        seek_thread.start()
        build_thread.start()
        send_thread.start()

        # Join threads
        seek_thread.join()
        build_thread.join()
        send_thread.join()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FRUIT_live by Bryce Castle")
        self.setGeometry(100, 100, 400, 300)
        
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)
        
        # Create a form layout to collect user information
        form_layout = QFormLayout()
        
        self.seconds_post_reveal = QLineEdit("0.61")
        self.match_length = QLineEdit(str(3+30+8+(60*2)+5))
        self.twitch_user = QLineEdit("firstinrobotics")
        self.event_year = QLineEdit()
        self.event_code = QLineEdit()
        self.event_title = QLineEdit()
        self.playlist_id = QLineEdit()
        
        form_layout.addRow("Seconds Post Reveal:", self.seconds_post_reveal)
        form_layout.addRow("Match Length:", self.match_length)
        form_layout.addRow("Twitch User:", self.twitch_user)
        form_layout.addRow("Event Year:", self.event_year)
        form_layout.addRow("Event Code:", self.event_code)
        form_layout.addRow("Event Title:", self.event_title)
        form_layout.addRow("Playlist ID:", self.playlist_id)
        
        self.program = QComboBox()
        self.program.addItems(["FRC", "FTC"])
        form_layout.addRow("Select program:", self.program)

        # set/check credentials via dialog pop-up window
        self.credentialsButton = QPushButton("Set/Check Credentials", self)
        self.credentialsButton.clicked.connect(lambda: CredDialog(self).exec())
        form_layout.addRow(self.credentialsButton)

        self.layout.addLayout(form_layout)
        
        self.action_button = QPushButton("Make the Sauce!")
        self.action_button.clicked.connect(self.toggle_sauce)
        self.layout.addWidget(self.action_button)
        
        # Create a horizontal layout for the status labels
        status_layout = QHBoxLayout()
        
        self.status_label_1 = QLabel(" SEEN: X")
        self.status_label_2 = QLabel("BUILT: X")
        self.status_label_3 = QLabel(" SENT: X")
        
        status_layout.addWidget(self.status_label_1)
        status_layout.addWidget(self.status_label_2)
        status_layout.addWidget(self.status_label_3)
        
        self.layout.addLayout(status_layout)

        self.stop_event = threading.Event()
    
    def toggle_sauce(self):
        if self.action_button.text() == "Make the Sauce!":
            self.make_sauce()
        else:
            self.stop_event.set()
            self.action_button.setText("Make the Sauce!")

    def make_sauce(self):
        user_data = {
            "program": self.program.currentText(),
            "post_reveal": float(self.seconds_post_reveal.text()),
            "match_length": float(self.match_length.text()),
            "twitch_user": self.twitch_user.text(),
            "event_year": int(self.event_year.text()),
            "event_code": self.event_code.text(),
            "event_title": self.event_title.text(),
            "playlist_ID": self.playlist_id.text(),
        }
        
        self.worker = Worker(user_data, self.stop_event)
        self.worker.progress_signal_1.connect(self.update_status_1)
        self.worker.progress_signal_2.connect(self.update_status_2)
        self.worker.progress_signal_3.connect(self.update_status_3)
        
        self.thread = threading.Thread(target=self.worker.make_sauce)
        self.thread.start()

        self.action_button.setText("Stop the Sauce!")

    def update_status_1(self, value):
        self.status_label_1.setText(f" SEEN: {value}")

    def update_status_2(self, value):
        self.status_label_2.setText(f" BUILT: {value}")

    def update_status_3(self, value):
        self.status_label_3.setText(f" SENT: {value}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())