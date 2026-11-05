import edge_tts
from pathlib import Path


VOICE_MAP = {
    "english": "en-US-AriaNeural",
    "hindi": "hi-IN-SwaraNeural",
    "hinglish": "hi-IN-SwaraNeural"
}


async def generate_audio(
    text,
    language,
    output_path
):

    language = language.lower()

    if language not in VOICE_MAP:
        raise ValueError(
            "Supported languages: English, Hindi, Hinglish"
        )

    voice = VOICE_MAP[language]

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    communicate = edge_tts.Communicate(
        text,
        voice
    )

    await communicate.save(
        str(output_path)
    )

    return str(output_path)


async def generate_scene_audio(
    scenes,
    language,
    output_dir
):

    language = language.lower()

    if language not in VOICE_MAP:
        raise ValueError(
            "Supported languages: English, Hindi, Hinglish"
        )

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    audio_files = []

    for index, scene in enumerate(scenes):

        narration = scene.get(
            "narration",
            ""
        ).strip()

        if not narration:
            continue

        scene_number = scene.get(
            "scene_number",
            index + 1
        )

        output_path = (
            output_dir /
            f"scene_{scene_number}.mp3"
        )

        await generate_audio(
            narration,
            language,
            output_path
        )

        audio_files.append(
            {
                "scene_number": scene_number,
                "audio_path": str(
                    output_path
                )
            }
        )

    return audio_files