#This Intro_capture.py script serves as an excellent reference or standalone test script for the *_intro_pending.mp4 concept.


from datetime import datetime, timedelta
import time
import json

def getMatchesFromFMS(*args, **kwargs):
    # Mock implementation for demonstration
    now = datetime.now()
    return [
        {'id': 1, 'start': now + timedelta(minutes=5)},
        {'id': 2, 'start': now + timedelta(minutes=15)},
    ]

def record_segment(stream, filename, duration):
    # Mock implementation for demonstration
    print(f"Recording {filename} from stream {stream} for {duration} seconds.")

def determine_next_match_id(fms_matches, current_time):
    """Return the next match after now."""
    future_matches = [m for m in fms_matches if m['start'].timestamp() > current_time]
    future_matches.sort(key=lambda m: m['start'])  # Soonest first
    return future_matches[0]['id'] if future_matches else None

# When Stop Intro is pressed
now = time.time()
matches = getMatchesFromFMS()
next_match_id = determine_next_match_id(matches, now)

stream = "default_stream"  # Placeholder for the actual stream object
intro_length = 10  # Placeholder for intro length in seconds

intro_clip_filename = f"{next_match_id}_intro_pending.mp4"
record_segment(stream, intro_clip_filename, duration=intro_length)

# You can even store this mapping in a file if running multiple processes
with open("pending_intros.json", "w", encoding="utf-8") as f:
    json.dump({next_match_id: intro_clip_filename}, f)