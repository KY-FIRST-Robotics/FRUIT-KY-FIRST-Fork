from datetime import datetime, timedelta

def determine_next_match_id(fms_matches, current_time):
    """Return the next match after now."""
    future_matches = [m for m in fms_matches if m['start'].timestamp() > current_time]
    future_matches.sort(key=lambda m: m['start'])  # Soonest first
    return future_matches[0]['id'] if future_matches else None

# When Stop Intro is pressed
now = time.time()
matches = getMatchesFromFMS(...)
next_match_id = determine_next_match_id(matches, now)

intro_clip_filename = f"{next_match_id}_intro_pending.mp4"
record_segment(stream, intro_clip_filename, duration=intro_length)

# You can even store this mapping in a file if running multiple processes
with open("pending_intros.json", "w") as f:
    json.dump({next_match_id: intro_clip_filename}, f)
    