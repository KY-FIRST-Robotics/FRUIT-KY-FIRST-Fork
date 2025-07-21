# FRUIT = FIRST Robotics Uploader from an Indiana Teammate
A python script (with GUI) for the automated processing of (long) livestream recordings into (short) match videos.

## How it works
1. Gets information about the matches from FIRST, includes start time and score post time
2. Splits the livestream recording into chucks based on those start & post times
3. Combines those chunks together into match videos
4. Generates a thumbnail using the match number and teams involved
5. Uploads the videos to YouTube
6. Notifies The Blue Alliance of the videos

## Upcoming Features
- [x] Blue Alliance Support
- [X] Use Twitch instead of a file for input
- [ ] Load a past CONFIG to save on input time
- [ ] Better handling of erroneous inputs
- [ ] Update up from Python 3.12.2
- [ ] Cool logo

## Setup for Developers; Getting FRUIT Running 
1. Download and setup Python 3 + Virtual Environment on IDE of choice
2. Install required packages; pip3 install -r requirements.txt
3. Add file "client_secrets" to TOOLS folder; take code from example.client_secrets and fill empty quotation marks with correct information
4. Add file "CREDENTIALS" to main folder; copy code from example.CREDENTIALS
5. Download the latest release version of ffmpeg https://www.gyan.dev/ffmpeg/builds/
6. Add ffmpeg's bin folder to system path
6A. Press Windows + S or navigate to the search bar
6B. Look up and go to "Edit environment variables for your account"
6C. Click Path, then click Edit
6D. Press Browse, then select the "bin" folder inside the ffmpeg folder
6E. Press Ok

## Setup for Developers; Operating FRUIT
1. Follow https://github.com/purduefirst/FRUIT/wiki/APIs and register for desired API keys
2. If livestreaming through Twitch, obtain Twitch Client ID and Client Secret
3. If livestreaming through YouTube, obtain Youtube API Key and Channel ID
4. Fill empty credentials fields with API information; in FRUIT or in the code
5. Input correct Season Year and Event Code in the event info tab of FRUIT; no event name needed
6. Once YouTube livestream is being recorded, the MP4 being recorded to can be used as a static video

## Guide for use
1. Welcome page: select correct program and enter and save all necessary credentials. Enter YouTube Username and copy + paste the channel ID if you plan to record and clip a YouTube livestream
2. Event Info: Enter season year and event code for the event, and pull FMS
3. YouTube Settings: Add your own description, tags, and if desired playlist link. Authenticate your YouTube account
4. Thumbnail Info: Add any image for sponsor logo if desired, enter correct information and test thumbnail
5. Match Timing: Can adjust to be more accurate for event's match timings. Should be fine as is
6. The Blue Alliance: If desired, input info and press "Verify TBA"
7. Video File: If clipping a Twitch stream, test Twitch connection. If clipping YouTube livestream, press the start recording
YouTube livestream button. If clipping a saved video, press select file and select your video.
8. If recording a YouTube livestream, after starting the recording, press select file, and go to TOOLS/recordings and find the mp4 file that is being recorded.
9. . Video File: Select the match type of the first match, enter the number of the first match, and enter the timestamp of that match.
Press "Play 4 Seconds" button to test.
10. Video File: Press "Bake Config" and then press "Make The Sauce." check the seen, built, and sent status to make sure it's running!
11. Notes: If recording a YouTube livestream, when clipping new matches as they appear, it will not be done automatically. You must
reenter the match type (if applicable), the match number, and timestamp, then rebake the config and press make the sauce again.
12. Notes: The "Stop Recording YouTube Livestream" button often isn't necessary, it's fine to keep recording the whole time. Use if
a new recording is desired or if you are finished.
13. Notes: Once clipping starts, if the app crashes or is accidentally restarted, the "Load CONFIG" button will bring back your saved info. Press Load CONFIG then scroll down and select the CONFIG file.




