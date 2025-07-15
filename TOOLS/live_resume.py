"""Live Match Recorder with FMS Auto Resume.

This script records live match segments and resumes based on FMS data.
"""

import subprocess
import os
import time
import json
import argparse
from typing import Optional

def load_credentials(path="CREDENTIALS"):
    """Load credentials from a JSON file."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)

def record_segment(input_stream_url: str, segment_filename: str, duration: Optional[int] = None):
    """Record a video segment from the input stream."""
    cmd = [
        'ffmpeg',
        '-y',
        '-i', input_stream_url,
        '-c:v', 'copy',
        '-c:a', 'copy'
    ]
    if duration:
        cmd += ['-t', str(duration)]
    cmd.append(segment_filename)

    print(f"🎥 Recording to {segment_filename}...")
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("⏹️ Manually stopped recording.")

def concat_segments(segment_files: list, output_filename: str):
    """Concatenate video segments into a single output file."""
    with open("segments.txt", "w", encoding="utf-8") as f:
        for seg in segment_files:
            f.write(f"file '{os.path.abspath(seg)}'\n")
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', 'segments.txt',
        '-c', 'copy',
        output_filename
    ]
    subprocess.run(cmd, check=True)
    os.remove("segments.txt")
    print(f"✅ Final video saved as: {output_filename}")

def rewrapMatches(matches, program):
    """Stub for rewrapMatches - replace with actual implementation."""
    return matches

def getMatchesFromFMS(year, event_code, program, username, key):
    """Stub for getMatchesFromFMS - replace with actual implementation."""
    # This function should return match data from the FMS API.
    return []

def wait_for_match_start(match_id: str, matches_url_data, program: str, poll_interval=5):
    """Polls FMS data every few seconds until actualStartTime appears for the given match_id."""
    print(f"⏳ Waiting for match {match_id} to begin...")
    while True:
        matches_updated = rewrapMatches(matches_url_data(), program)
        target_match = next((m for m in matches_updated if m['id'] == match_id), None)
        if target_match and target_match.get('start') is not None:
            print(f"🚦 Match {match_id} started at {target_match['start']}")
            return target_match
        time.sleep(poll_interval)

def capture_match_with_fms(
    input_stream_url: str,
    match_id: str,
    year: int,
    event_code: str,
    program: str = "FRC",
    output_dir: str = "output_clips",
    with_intro: bool = False,
    intro_duration: int = 90
):
    """Capture a match with FMS auto resume and optional intro clipping."""
    os.makedirs(output_dir, exist_ok=True)
    intro_file = os.path.join(output_dir, f"{match_id}_intro.mp4")
    match_file = os.path.join(output_dir, f"{match_id}_match.mp4")
    final_output = os.path.join(output_dir, f"{match_id}_with_intro.mp4")

    credentials = load_credentials()
    def get_fms_data():
        return getMatchesFromFMS(year, event_code, program, credentials["FRC_username"], credentials["FRC_key"])

    match_data = wait_for_match_start(match_id, get_fms_data, program)
    start_time = match_data["start"].timestamp()

    # Check if there's a pending intro file instead of freshly recorded one
    pending_intro = os.path.join(output_dir, f"{match_id}_intro_pending.mp4")
    if os.path.exists(pending_intro):
        print(f"🔗 Found intro for {match_id}, attaching it to match video...")
        concat_segments([pending_intro, match_file], final_output)
        os.remove(pending_intro)
        os.remove(match_file)
    elif with_intro:
        print(f"🎞️ Attaching freshly recorded intro to {match_id}...")
        concat_segments([intro_file, match_file], final_output)
        os.remove(intro_file)
        os.remove(match_file)
    else:
        final_output = match_file


    time_until_match = start_time - time.time()
    if time_until_match > 0:
        print(f"⏰ Waiting {time_until_match:.2f}s until match start...")
        time.sleep(time_until_match)

    print(f"🎬 Recording match for 180s...")
    record_segment(input_stream_url, match_file, duration=180)

    if with_intro:
        concat_segments([intro_file, match_file], final_output)
        os.remove(intro_file)
        os.remove(match_file)
    else:
        final_output = match_file

    print(f"🎞️ Finished match {match_id}. Saved as: {final_output}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Match Recorder with FMS Auto Resume and Optional Intro Clipping")
    parser.add_argument("input_stream_url", help="Stream input (e.g. /dev/video0, rtsp://...)")
    parser.add_argument("match_id", help="Match ID (e.g. Q1, P2, F1)")
    parser.add_argument("year", type=int, help="Season year (e.g. 2025)")
    parser.add_argument("event_code", help="Event code (e.g. 'SEVI')")
    parser.add_argument("--program", default="FRC", help="FRC or FTC")
    parser.add_argument("--output_dir", default="output_clips", help="Output folder")
    parser.add_argument("--with_intro", action="store_true", help="Include team introductions")
    parser.add_argument("--intro_duration", type=int, default=90, help="Intro clip duration in seconds")

    args = parser.parse_args()

    capture_match_with_fms(
        input_stream_url=args.input_stream_url,
        match_id=args.match_id,
        year=args.year,
        event_code=args.event_code,
        program=args.program,
        output_dir=args.output_dir,
        with_intro=args.with_intro,
        intro_duration=args.intro_duration
    )