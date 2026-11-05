import subprocess
from pathlib import Path


def get_audio_duration(audio_path):

    audio_path = Path(audio_path)

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )

    duration = float(
        result.stdout.strip()
    )

    return duration