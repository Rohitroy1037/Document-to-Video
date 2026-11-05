import json
from pathlib import Path

from app.services.audio_duration import get_audio_duration


def create_audio_plan(
    audio_files,
    output_path
):

    audio_plan = []

    for audio in audio_files:

        audio_path = Path(
            audio["audio_path"]
        )

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )

        duration = get_audio_duration(
            audio_path
        )

        audio_plan.append(
            {
                "scene_number": audio["scene_number"],
                "audio_path": str(audio_path),
                "duration": duration
            }
        )

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "scenes": audio_plan
            },
            file,
            indent=2,
            ensure_ascii=False
        )

    return audio_plan


def synchronize_scene_plan(
    scene_plan,
    audio_plan
):

    audio_map = {
        item["scene_number"]: item
        for item in audio_plan.get(
            "scenes",
            []
        )
    }

    synchronized_scenes = []

    for index, scene in enumerate(
        scene_plan.get("scenes", [])
    ):

        scene_number = scene.get(
            "scene_number",
            index + 1
        )

        if scene_number not in audio_map:
            raise ValueError(
                f"Audio duration missing for scene {scene_number}"
            )

        updated_scene = scene.copy()

        updated_scene["duration"] = float(
            audio_map[
                scene_number
            ]["duration"]
        )

        synchronized_scenes.append(
            updated_scene
        )

    return {
        "scenes": synchronized_scenes
    }