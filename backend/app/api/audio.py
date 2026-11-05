from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

from app.services.tts_service import generate_scene_audio
from app.services.audio_plan import (
    create_audio_plan,
    synchronize_scene_plan
)


router = APIRouter()


SCENE_DIR = Path("storage/scenes")
AUDIO_DIR = Path("storage/audio")


AUDIO_DIR.mkdir(
    parents=True,
    exist_ok=True
)


@router.post("/audio/{document_id}/{language}")
async def create_audio(
    document_id: str,
    language: str
):

    language = language.lower()

    scene_path = (
        SCENE_DIR /
        f"{document_id}_{language}.json"
    )

    if not scene_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                "Scene plan not found. "
                "Run /scenes first."
            )
        )

    try:

        # --------------------------------
        # Load scene plan
        # --------------------------------

        with open(
            scene_path,
            "r",
            encoding="utf-8"
        ) as input_file:

            scene_plan = json.load(
                input_file
            )

        scenes = scene_plan.get(
            "scenes",
            []
        )

        if not scenes:

            raise HTTPException(
                status_code=400,
                detail="No scenes found."
            )

        # --------------------------------
        # Production audio directory
        # --------------------------------

        audio_dir = (
            AUDIO_DIR /
            f"scenes_{document_id}_{language}"
        )

        audio_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        # --------------------------------
        # Generate scene audio
        # --------------------------------

        audio_files = await generate_scene_audio(
            scenes,
            language,
            audio_dir
        )

        if not audio_files:

            raise HTTPException(
                status_code=400,
                detail="No audio was generated."
            )

        # --------------------------------
        # Create audio plan
        # --------------------------------

        audio_plan_path = (
            audio_dir /
            "audio_plan.json"
        )

        audio_plan = create_audio_plan(
            audio_files,
            audio_plan_path
        )

        # --------------------------------
        # Synchronize scene durations
        # --------------------------------

        synchronized_scene_plan = (
            synchronize_scene_plan(
                scene_plan,
                {
                    "scenes": audio_plan
                }
            )
        )

        # --------------------------------
        # Save synchronized scene plan
        # --------------------------------

        with open(
            scene_path,
            "w",
            encoding="utf-8"
        ) as output_file:

            json.dump(
                synchronized_scene_plan,
                output_file,
                indent=2,
                ensure_ascii=False
            )

        # --------------------------------
        # Calculate total duration
        # --------------------------------

        total_duration = sum(
            float(
                item["duration"]
            )
            for item in audio_plan
        )

        return {
            "status": "success",
            "document_id": document_id,
            "language": language,
            "audio_directory": str(
                audio_dir
            ),
            "audio_plan": str(
                audio_plan_path
            ),
            "scenes": audio_plan,
            "total_duration": round(
                total_duration,
                3
            )
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )