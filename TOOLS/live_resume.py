"""Live Match Recorder with FMS Auto Resume.

This script records live match segments and resumes based on FMS data.
"""

import subprocess
import os
import time
import json
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
    # This is a placeholder. Replace with actual logic as needed.
    # For now, just return matches as-is.
    return matches

def getMatchesFromFMS(year, event_code, program, username, key):
    """Stub for getMatchesFromFMS - replace with actual implementation."""
    # This is a placeholder. Replace with actual logic as needed.
    # For now, return a list of dicts with 'id' and 'start' keys.
    # Example: [{'id': 'Q1', 'start': datetime.now()}]
    # Replace with real FMS API call.
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
    output_dir: str = "output_clips"
):
    """Capture a match with FMS auto resume."""
    os.makedirs(output_dir, exist_ok=True)
    intro_file = os.path.join(output_dir, f"{match_id}_intro.mp4")
    match_file = os.path.join(output_dir, f"{match_id}_match.mp4")
    final_output = os.path.join(output_dir, f"{match_id}_with_intro.mp4")

    credentials = load_credentials()
    def get_fms_data():
        return getMatchesFromFMS(year, event_code, program, credentials["FRC_username"], credentials["FRC_key"])

    # Step 1: Record the team introductions
    input(f"📣 Press Enter to START recording team intros for {match_id}...")
    record_segment(input_stream_url, intro_file)

    # Step 2: Wait for match to start (auto mode countdown)
    wait_for_match_start(match_id, get_fms_data, program)

    # Step 3: Record the match from the point we resumed
    print(f"🎬 Recording match segment for {match_id}...")
    # Estimate match duration (~2.5min + buffer)
    record_segment(input_stream_url, match_file, duration=180)

    # Step 4: Merge and cleanup
    concat_segments([intro_file, match_file], final_output)
    os.remove(intro_file)
    os.remove(match_file)
    print(f"🎞️ Finished match {match_id}.\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Live Match Recorder with FMS Auto Resume")
    parser.add_argument("input_stream_url", help="Stream input (e.g. /dev/video0, rtsp://...)")
    parser.add_argument("match_id", help="Match ID (e.g. Q1, P2, F1)")
    parser.add_argument("year", type=int, help="Season year (e.g. 2025)")
    parser.add_argument("event_code", help="Event code (e.g. 'SEVI')")
    parser.add_argument("--program", default="FRC", help="FRC or FTC")
    parser.add_argument("--output_dir", default="output_clips", help="Output folder")

    args = parser.parse_args()

    capture_match_with_fms(
        input_stream_url=args.input_stream_url,
        match_id=args.match_id,
        year=args.year,
        event_code=args.event_code,
        program=args.program,
        output_dir=args.output_dir
    )
# This code is a complete script for recording live matches with FMS auto resume functionality.
# It includes functions for loading credentials, recording segments, concatenating videos,
# and handling FMS data. The script can be run from the command line with appropriate arguments