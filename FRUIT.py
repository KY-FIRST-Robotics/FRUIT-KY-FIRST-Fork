# imports for GUI
from PyQt6.QtWidgets import QApplication, QWidget,  QFormLayout, QGridLayout, QTabWidget, QPushButton, QLineEdit, QPlainTextEdit, QLabel, QFileDialog, QComboBox, QCheckBox
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import QSize, QUrl, QTimer, QThread, pyqtSignal

import random       # random thumbnail generation
import datetime     # str conversion and timeDelta
import os           # file IO
import json         # CONFIG handling

# libraries for splitting and combining video
from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.audio.fx.all import audio_fadeout, audio_fadein

# my functions, see python scripts in TOOLS
from TOOLS.CredentialsPopUp import CredDialog
from TOOLS.FMS import getMatchesFromFMS
from TOOLS.YouTube import authenticate_youtube
from TOOLS.YouTube import upload_video
from TOOLS.thumbnails import generateThumbnail
from TOOLS.TBA import postTheBlueAlliance
from TOOLS.TBA import translateMatchString

# prepare related directories
if not os.path.exists('input/'):
    os.makedirs('input/')
if not os.path.exists('output/'):
    os.makedirs('output/')
if not os.path.exists('output/thumbnails/'):
    os.makedirs('output/thumbnails/')

# translator for symbols
translateSymbol = {'M': 'Playoffs', 'Q': 'Quals', 'F': 'Finals'}

class makeTheSauceThread(QThread):
    result_ready = pyqtSignal(int)

    def __init__(self):
        super().__init__()
    
    def passData(self, matches, YouTube=None):
        self.matches = matches
        self.YouTube = YouTube
    
    def makeTheSauce(self):
        with open('CONFIG') as json_file:
            CONFIG = json.load(json_file)

        # get information about the video to determine which matches it contains
        fileDuration = VideoFileClip(CONFIG['video']['filePath']).duration
        fileMatchStart = self.matches[CONFIG['video']['matchID']]['start']
        fileTimeEnd = fileMatchStart+datetime.timedelta(seconds=fileDuration)
        fileSecStart = (CONFIG['video']['matchTime'][0]*60)+CONFIG['video']['matchTime'][1]

        # which matches are contained in the input video?
        matchesInFile = {k: v for k, v in self.matches.items() if (v['start'] >= fileMatchStart)*(v['post'] < fileTimeEnd)}
        print(len(list(matchesInFile.keys())), 'matches in file (expecting 39 or 40)')

        # clip each match
        for matchID, matchInfo in matchesInFile.items():
            print('Starting:'+matchID)

            # determine video timestamps of notable events
            secStart = (matchInfo['start'] - fileMatchStart).total_seconds() + fileSecStart 
            secPost = (matchInfo['post'] - fileMatchStart).total_seconds() + fileSecStart

            # define output filename
            outputFileName = str(CONFIG['season']['year'])+' '+CONFIG['event']['name']+' '+translateSymbol[matchID[0]]+' '+matchID[1:]+'.mp4'

            # if the file does not already exist, write one
            if not os.path.exists('output/'+outputFileName):
                print(matchID+' did not exist!')
                with VideoFileClip(CONFIG['video']['filePath']) as video:
                    # generate it's thumbnail
                    thumbnailLoc = generateThumbnail(matchID, matchInfo, CONFIG['event']['details'])

                    # clip the match and the scores, adding audio fades to taste
                    match = audio_fadein(video.subclip(secStart - CONFIG['season']['secondsBeforeStart'], secStart + CONFIG['season']['secondsOfMatch'] + CONFIG['season']['secondsAfterEnd']), 0.5)
                    scores = audio_fadeout(video.subclip(secPost + CONFIG['season']['secondsBeforePost'], secPost + CONFIG['season']['secondsAfterPost']), 2)

                    # merge together match and scores
                    final = concatenate_videoclips([match, scores])

                    # save the results as a file
                    final.write_videofile('output/'+outputFileName, audio_codec='aac')

                    # prepare YouTube title, description, tags
                    request_body = {
                        "snippet": {
                            "title": outputFileName.split('.mp4')[0],
                            "description": CONFIG['YouTube']['description'],
                            "categoryId": "28",  # Category ID for "Science & Technology"
                            "tags": CONFIG['YouTube']['tags'].split(',') + [CONFIG['event']['code'], str(CONFIG['season']['year']), matchID, "trimFRC_BCC"]
                        },
                        "status": {
                            "privacyStatus": "unlisted"
                        }
                    }
                    
                    # upload to YouTube
                    videoID = upload_video(self.YouTube, 'output/'+outputFileName, request_body, thumbnailLoc, playlistID=CONFIG['YouTube']['playlist'])

                    # post video to TBA
                    data = {translateMatchString(matchID): videoID}
                    response = postTheBlueAlliance(CONFIG['TBA']['Auth_Id'], CONFIG['TBA']['Auth_Secret'], CONFIG['TBA']['eventKey'], data)

                    if response.status_code != 200:
                        print('Issue with TBA API for some reason?')

                    print('Done:'+matchID+' ('+videoID+')')
            
        return len(matchesInFile.items())

    def run(self):
        result = self.makeTheSauce()
        self.result_ready.emit(result)

class MainWindow(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logoSponsorFilepath = None
        self.videoFilepath = None

        '''
        set window title, size and layout
        '''
        self.setWindowTitle('FRUIT by Bryce Castle')
        self.setGeometry(500, 300, 800, 400)
        main_layout = QGridLayout(self)
        self.setLayout(main_layout)
        self.tab = QTabWidget(self)

        '''
        WELCOME PAGE
         - information on how to use tool
         - mostly text
        '''
        bodyText = "<ol style='font-size: 16px !important;'><li><b>Event Info</b>: used to obtain match details from FMS, learn more at https://frc-events.firstinspires.org/services/api</li><li>Connect to your YouTube account using the browser. Define <b>YouTube Settings</b> for video upload.</li><li>Supply <b>Thumbnail Info</b> and test its generation.</li><li>Set <b>Match Timing</b> offsets in second, relative to match start and scores post (in seconds).</li><li>Select the <b>Video File</b> to be trimmed.</li><li>Connect to <b>The Blue Alliance</b> for match video visibility.</li><li><b>Bake CONFIG</b> to save on future re-entry time.</li><li>Click the <b>Make The Sauce</b> button to get everything rolling!"

        page_welcome = QWidget(self)
        layout = QFormLayout()
        page_welcome.setLayout(layout)
        layout.addRow(QLabel("<h1>FIRST Robotics Uploader from an Indiana Teammate</h1>\n<i>Make each tab green then you're ready to proceed.</i>"))
        layout.addRow(QLabel(bodyText))
        # select program (FRC/FTC)
        self.program = QComboBox()
        self.program.addItems(["FRC", "FTC"])
        layout.addRow("Select program:", self.program)
        # set/check credentials via dialog pop-up window
        self.credentialsButton = QPushButton("Set/Check Credentials", self)
        self.credentialsButton.clicked.connect(lambda: CredDialog(self).exec())
        layout.addRow(self.credentialsButton)

        
        '''
        EVENT PAGE
         - Season Year
         - Event Code & Name
         - Pull from FMS
        '''
        page_event = QWidget(self)
        layout = QGridLayout()
        page_event.setLayout(layout)
        layout.addWidget(QLabel('Season Year:'), 0, 0); self.season_year = QLineEdit(self); layout.addWidget(self.season_year, 0, 1)
        layout.addWidget(QLabel('Event Code:'), 1, 0); self.event_code = QLineEdit(self); layout.addWidget(self.event_code, 1, 1)
        layout.addWidget(QLabel('Event Name:'), 2, 0); self.event_name = QLineEdit(self); layout.addWidget(self.event_name, 2, 1)
        # FMS pull button
        self.textFMS = QLabel('<font color="red">Event not yet pulled</font>')
        self.button_FMS = QPushButton('Pull FMS')
        self.button_FMS.clicked.connect(lambda: self.handleFMS(self.season_year.text(), self.event_code.text(), self.textFMS))
        layout.addWidget(self.button_FMS, 4, 0)
        layout.addWidget(self.textFMS, 4, 1)
        

        '''
        YOUTUBE PAGE
         - YouTube Authentication
         - YouTube video description, tags, playlist
        '''
        page_YouTube = QWidget(self)
        layout = QFormLayout()
        page_YouTube.setLayout(layout)
        layout.addRow(QLabel('<b>Connect the YouTube channel you want to upload to, accepting both permissions (read & write videos)</b>'))
        # Authentication
        self.textYouTube = QLabel('<font color="red">YouTube not yet authenticated</font>')
        self.button_FMS = QPushButton('Connect to YouTube')
        self.button_FMS.clicked.connect(self.handleYouTube)
        layout.addRow(self.button_FMS, self.textYouTube)
        # Description
        self.video_description = QPlainTextEdit("Footage of this event is courtesy of FIRST Indiana Robotics.\n\nFollow us on Twitter (@FIRSTINRobotics), Facebook (FIRST Indiana Robotics), and Twitch (FIRSTINRobotics).\n\nFor more information and future event schedules, visit our website: https://www.firstindianarobotics.org")
        layout.addRow('Description:', self.video_description)
        # Tags
        self.video_tags = QLineEdit('FIRST Robotics Competition, FRC, FIRST Indiana Robotics, FIN')
        layout.addRow(QLabel('Tags (comma-delimited) :'), self.video_tags)
        layout.addRow(QLabel('<i>program will automatically add year & event code</i>'))
        # Playlist
        self.video_playlist = QLineEdit("https://www.youtube.com/playlist?list=")
        layout.addRow('Playlist URL (optional):', self.video_playlist)
        

        '''
        THUMBNAIL PAGE
         - Sponsor Image
         - Verbose event details
         - Random thumbnail generator
        '''
        page_thumbnail = QWidget(self)
        layout = QFormLayout()
        page_thumbnail.setLayout(layout)
        layout.addRow(QLabel('<b>Choose a sponsor logo OR fill out more event info for YouTube thumbnail</b>'))
        # Sponsor Image
        self.img_EventSponsor = QPushButton('Select File')
        self.img_EventSponsor.clicked.connect(lambda: self.getFileSponsorImage(self.img_EventSponsor))
        layout.addRow('Sponsor Logo:', self.img_EventSponsor)
        # Verbose event details
        layout.addRow(QLabel('⸻ or ⸻'))
        self.eventLocation = QLineEdit(self);  layout.addRow('Location:', self.eventLocation)
        self.eventCity = QLineEdit(self);  layout.addRow('City:', self.eventCity)
        self.eventDates = QLineEdit(self);  layout.addRow('Dates:', self.eventDates)
        # Force text details over sponsor logo
        self.thumbnail_force = QCheckBox('Force using additional event info')
        layout.addRow(self.thumbnail_force)
        # Test thumbnail using random generator
        self.image_thumbnail = QLabel('<font color="red">Generate a test thumbnail</font>')
        self.button_thumbnail = QPushButton('Test Thumbnail')
        self.button_thumbnail.clicked.connect(lambda: self.handleThumbnail([self.eventLocation.text(), self.eventCity.text(), self.eventDates.text()], self.image_thumbnail, self.thumbnail_force.isChecked()))
        layout.addRow(self.button_thumbnail, self.image_thumbnail)

        '''
        TIMINGS PAGE
         - seconds before match starts (to hear MC countdown)
         - match duration (auto + buzzer + teleop)
         - seconds to show after end of game
         - seconds to wait after post (reval animation)
         - seconds to show score
        '''
        page_timings = QWidget(self)
        layout = QFormLayout()
        page_timings.setLayout(layout)
        self.season_secondsBefore = QLineEdit('3'); layout.addRow('Seconds Before :', self.season_secondsBefore)
        self.season_matchDuration = QLineEdit('155'); layout.addRow('Match Duration :', self.season_matchDuration)
        self.season_secondsAfterEnd = QLineEdit('5'); layout.addRow('Seconds After End :', self.season_secondsAfterEnd)
        self.season_secondsBeforePost = QLineEdit('-7.25'); layout.addRow('Seconds Before Post :', self.season_secondsBeforePost)
        self.season_secondsAfterPost = QLineEdit('23.92'); layout.addRow('Seconds After Post :', self.season_secondsAfterPost)
        layout.addRow(QLabel('<i>These should add to 179.94 to get a 3:00 video on YouTube</i>'))

        '''
        VIDEO FILE
         - select video file
         - provide reference match (# and time)
         - watch 4 seconds of clip
        '''
        page_video = QWidget(self)
        layout = QFormLayout()
        page_video.setLayout(layout)
        self.mp4_VOD = QPushButton('Select File')
        self.mp4_VOD.clicked.connect(self.getFileVideo)
        layout.addRow('Video File:', self.mp4_VOD)
        # reference match details
        self.match_type = QComboBox(); self.match_type.addItems(["Q = Quals", "M = Playoffs", "F = Finals"])
        layout.addRow('First Match Type:', self.match_type)
        self.match_number_ref = QLineEdit(); layout.addRow('First Match Number:', self.match_number_ref)
        self.timestamp_label = QLabel("Enter timestamp (mm:ss):")
        self.timestamp_input = QLineEdit()
        layout.addRow('Enter timestamp (mm:ss):', self.timestamp_input)
        # Create a video widget and add it to the layout
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(480, 270)
        self.play_button = QPushButton("Play 4 Seconds")
        self.play_button.setStyleSheet('color: red')
        self.play_button.clicked.connect(self.play_video)
        layout.addRow(self.play_button, self.video_widget)
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        '''
        TBA PAGE
         - Season Year
         - Event Code & Name
         - Pull from FMS
        '''
        page_TBA = QWidget(self)
        layout = QFormLayout()
        page_TBA.setLayout(layout)

        self.TBA_eventCode = QLineEdit(); layout.addRow(QLabel('TBA event code:'), self.TBA_eventCode)
        self.TBA_AuthID = QLineEdit(); layout.addRow(QLabel('Associated Auth ID:'), self.TBA_AuthID)
        self.TBA_AuthSecret = QLineEdit(); layout.addRow(QLabel('Associated Auth Secret:'), self.TBA_AuthSecret)
        
        # FMS pull button
        self.button_TBA = QPushButton("Verify TBA"); self.button_TBA.setStyleSheet('color: red')
        self.button_TBA.clicked.connect(lambda: self.handleTBA(self.TBA_AuthID.text(), self.TBA_AuthSecret.text(), self.TBA_eventCode.text()))
        layout.addRow(self.button_TBA)

        '''
        add all tabs to window
        '''
        self.tab.addTab(page_welcome, 'Welcome')
        self.tab.addTab(page_event, 'Event Info')
        self.tab.addTab(page_YouTube, 'YouTube Settings')
        self.tab.addTab(page_thumbnail, 'Thumbnail Info')
        self.tab.addTab(page_timings, 'Match Timing')
        self.tab.addTab(page_video, 'Video File')
        self.tab.addTab(page_TBA, 'The Blue Alliance')
        # set tab colors
        self.tab.tabBar().setTabTextColor(1, QColor('red'))
        self.tab.tabBar().setTabTextColor(2, QColor('red'))
        self.tab.tabBar().setTabTextColor(3, QColor('red'))
        self.tab.tabBar().setTabTextColor(4, QColor('green'))
        self.tab.tabBar().setTabTextColor(5, QColor('red'))
        self.tab.tabBar().setTabTextColor(6, QColor('red'))
        main_layout.addWidget(self.tab)

        '''
        Bake CONFIG button
        '''
        self.bake_config_JSON = QPushButton('Bake CONFIG')
        self.bake_config_JSON.clicked.connect(lambda: self.bakeCONFIG(self.bake_config_JSON))
        main_layout.addWidget(self.bake_config_JSON)

        self.startThreadButton = QPushButton('Make The Sauce')
        self.startThreadButton.clicked.connect(self.start_sauce_thread)
        main_layout.addWidget(self.startThreadButton)

        self.thread = makeTheSauceThread()
        self.thread.result_ready.connect(self.on_sauce_made)

        self.show()
    
    def start_sauce_thread(self):
        self.startThreadButton.setEnabled(False)
        self.thread.passData(self.matches, self.YouTube)
        self.thread.start()

    def on_sauce_made(self, result):
        self.startThreadButton.setText(f"{result} matches processed!")
        self.startThreadButton.setEnabled(True)
    
    def play_video(self):
        # Get the timestamp from the input field and convert it to milliseconds
        timestamp = self.timestamp_input.text()
        self.match_timeMin, self.match_timeSec = map(float, timestamp.split(':'))
        position = int((self.match_timeMin * 60 + self.match_timeSec) * 1000)
        self.media_player.setPosition(position)
        self.media_player.play()

        # Pause the video after 4 seconds
        QTimer.singleShot(4000, self.media_player.pause)
        self.tab.tabBar().setTabTextColor(5, QColor('green'))
        self.play_button.setStyleSheet('color: green')
    
    def getFileVideo(self, button):
        response = QFileDialog.getOpenFileName(
            parent=self,
            caption='Select a file',
            directory=os.getcwd(),
            filter='Video File (*.mp4)'
        )
        
        self.videoFilepath = response[0]
        
        self.mp4_VOD.setText('📁'+response[0].split('/')[-1])
        self.media_player.setSource(QUrl.fromLocalFile(response[0]))
    
    def getFileSponsorImage(self, button):
        response = QFileDialog.getOpenFileName(
            parent=self,
            caption='Select a file',
            directory=os.getcwd(),
            filter='Image File (*.png *.jpg)'
        )

        self.logoSponsorFilepath = response[0]

        button.setText('📁'+response[0].split('/')[-1])
    
    def handleFMS(self, year, eventCode, text):
        text.setText('<font color="aqua">Loading event from FMS...</font>')
        text.repaint()

        try:
            self.matches = getMatchesFromFMS(year, eventCode)
            text.setText('<font color="green">'+str(len(self.matches.keys()))+' matches found for '+eventCode+'.</font>')
            self.tab.tabBar().setTabTextColor(1, QColor('green'))
        except json.JSONDecodeError:
            text.setText('<font color="red">Event does not exist!</font>')
            self.tab.tabBar().setTabTextColor(1, QColor('red'))
    
    def handleTBA(self, TBA_Auth_Id, TBA_Auth_Secret, TBA_eventKey):
        self.button_TBA.setText('Testing TBA API...')
        self.button_TBA.setStyleSheet('color: aqua')
        self.button_TBA.repaint()

        response = postTheBlueAlliance(TBA_Auth_Id, TBA_Auth_Secret, TBA_eventKey)

        if response.status_code == 200:
            self.button_TBA.setText('TBA API Verified!')
            self.button_TBA.setStyleSheet('color: green')
            self.button_TBA.repaint()
            self.tab.tabBar().setTabTextColor(6, QColor('green'))
        else:
            self.button_TBA.setText('Issue with TBA API!')
            self.button_TBA.setStyleSheet('color: red')
            self.button_TBA.repaint()

    
    def handleYouTube(self):
        self.textYouTube.setText('<font color="aqua">Authenticate using browser...</font>')
        self.textYouTube.repaint()

        self.YouTube = authenticate_youtube()
        self.textYouTube.setText('<font color="green">YouTube authenticated!</font>')
        self.tab.tabBar().setTabTextColor(2, QColor('green'))
    
    def handleThumbnail(self, data, image, forceText = False):
        image.setText('<font color="aqua">Generating thumbnail...</font>')
        image.repaint()

        typMatchNumb = {'Q':70, 'M':13, 'F':3}
        matchType = random.choices(['Q', 'M', 'F'], [0.8, 0.15, 0.05])[0]
        matchNumb = random.randint(1, typMatchNumb[matchType])
        matchID = matchType+str(matchNumb)

        teams = [random.randint(1, 11000) for x in range(6)]
        matchInfo = {'start':datetime.datetime.now(), 'post': datetime.datetime.now()+datetime.timedelta(seconds=155), 'teamsRed': teams[0:3], 'teamsBlue' : teams[3:6]}

        eventDetails = data[0]+"\n"+data[1]+"\n"+data[2]

        if forceText:
            generateThumbnail(matchID, matchInfo, eventDetails, None, 'trial')
        elif self.logoSponsorFilepath != None:
            generateThumbnail(matchID, matchInfo, None, self.logoSponsorFilepath, 'trial')
        else:
            generateThumbnail(matchID, matchInfo, eventDetails, None, 'trial')
        
        image.setPixmap(QPixmap('trial.png').scaled(QSize(424, 240)))
        self.tab.tabBar().setTabTextColor(3, QColor('green'))
    
    def bakeCONFIG(self, button):
        try:
            CONFIG = {
                'event' : {
                    'code' : self.event_code.text(),
                    'name' : self.event_name.text(),
                    'details' : self.eventLocation.text()+'\n'+self.eventCity.text()+'\n'+self.eventDates.text(),
                    'logo' : self.logoSponsorFilepath,
                    'forceDetails' : bool(self.thumbnail_force.isChecked())
                },
                'season' : {
                    'year' : -1 if self.season_year.text() == '' else int(self.season_year.text()),
                    'secondsBeforeStart' : float(self.season_secondsBefore.text()),
                    'secondsOfMatch' : float(self.season_matchDuration.text()), #auto + bell (~5) + teleop
                    'secondsAfterEnd' : float(self.season_secondsAfterEnd.text()),
                    'secondsBeforePost' : float(self.season_secondsBeforePost.text()),
                    'secondsAfterPost' : float(self.season_secondsAfterPost.text())
                },
                'YouTube' : {
                    'description' : self.video_description.toPlainText(),
                    'tags' : self.video_tags.text(),
                    'playlist' : self.video_playlist.text().split('?list=')[-1]
                },
                'video' : {
                    'filePath' : self.videoFilepath,
                    'matchID' : self.match_type.currentText()[0] + self.match_number_ref.text(),
                    'matchTime' : (self.match_timeMin, self.match_timeSec)
                },
                'TBA' : {
                    'Auth_Id' : self.TBA_AuthID.text(),
                    'Auth_Secret': self.TBA_AuthSecret.text(),
                    'eventKey': self.TBA_eventCode.text()
                }
            }

            with open("CONFIG", "w") as file:
                json.dump(CONFIG, file, indent=2)
            button.setStyleSheet('color: green')
            button.setText('Bake CONFIG: SUCCESS!')
        
        except AttributeError:
            button.setStyleSheet('color: red')
            button.setText('Bake CONFIG: ERROR')

import sys
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec())