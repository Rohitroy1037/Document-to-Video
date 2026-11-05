
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

from app.services.video_renderer import render_video
from app.services.subtitle_generator import create_subtitle_file


router = APIRouter()

AUDIO_PLAN_DIR = Path("storage/audio")
SCENE_DIR = Path("storage/scenes")
DOCUMENT_DIR = Path("storage/documents")
PAGE_DIR = Path("storage/pages")
VIDEO_DIR = Path("storage/videos")
SUBTITLE_DIR = Path("storage/subtitles")


for directory in [VIDEO_DIR, SUBTITLE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


@router.post("/video/{document_id}/{language}")
async def create_video(document_id: str, language: str):

    language = language.lower()

    scene_path = (
        SCENE_DIR / f"{document_id}_{language}.json"
    )

    audio_plan_path = (
        AUDIO_PLAN_DIR
        / f"scenes_{document_id}_{language}"
        / "audio_plan.json"
    )

    document_path = (
        DOCUMENT_DIR / f"{document_id}.json"
    )

    page_dir = PAGE_DIR / document_id

    subtitle_path = (
        SUBTITLE_DIR / f"{document_id}_{language}.srt"
    )

    # Check required files
    if not scene_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Scene plan not found. Run /scenes first."
        )

    if not audio_plan_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio plan not found. Generate audio first."
        )

    if not document_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Original document metadata not found."
        )

    if not page_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Document visuals directory not found: {page_dir}"
        )

    try:
        # Load the saved scene plan
        with open(scene_path, "r", encoding="utf-8") as file:
            scene_plan = json.load(file)

        # Load the audio plan
        with open(audio_plan_path, "r", encoding="utf-8") as file:
            audio_plan = json.load(file)

        # Load original document metadata.
        # This is the source of truth for PDF vs PPTX.
        with open(document_path, "r", encoding="utf-8") as file:
            document = json.load(file)

        document_type = str(
            document.get("document_type", "")
        ).lower()

        if document_type not in {"pdf", "pptx"}:
            raise ValueError(
                f"Unsupported document type: {document_type}"
            )

        # Explicitly pass the document type to the renderer.
        scene_plan["document_type"] = document_type

        scenes = scene_plan.get("scenes", [])
        audio_scenes = audio_plan.get("scenes", [])

        if not scenes:
            raise HTTPException(
                status_code=400,
                detail="No scenes found in the scene plan."
            )

        if not audio_scenes:
            raise HTTPException(
                status_code=400,
                detail="No audio scenes found in the audio plan."
            )

        # Check that the correct visual files exist.
        first_image_name = (
            "slide_1.png"
            if document_type == "pptx"
            else "page_1.png"
        )

        first_image_path = page_dir / first_image_name

        if not first_image_path.exists():
            raise FileNotFoundError(
                f"Expected {document_type.upper()} visual not found: "
                f"{first_image_path}"
            )

        # Match audio entries with their scene numbers.
        audio_map = {}

        for item in audio_scenes:
            if "scene_number" not in item:
                raise ValueError(
                    "Audio plan contains an entry without scene_number."
                )

            audio_map[int(item["scene_number"])] = item

        # Update scene durations to match actual audio durations.
        subtitle_scene_plan = {
            "scenes": []
        }

        total_duration = 0.0

        for index, scene in enumerate(scenes, start=1):
            scene_number = int(
                scene.get("scene_number", index)
            )

            if scene_number not in audio_map:
                raise ValueError(
                    f"Audio missing for scene {scene_number}."
                )

            audio_duration = float(
                audio_map[scene_number]["duration"]
            )

            if audio_duration <= 0:
                raise ValueError(
                    f"Invalid audio duration for scene {scene_number}."
                )

            total_duration += audio_duration

            updated_scene = scene.copy()
            updated_scene["scene_number"] = scene_number
            updated_scene["duration"] = audio_duration

            subtitle_scene_plan["scenes"].append(
                updated_scene
            )

        # Generate subtitles based on actual audio durations.
        create_subtitle_file(
            subtitle_scene_plan,
            subtitle_path
        )

        output_path = (
            VIDEO_DIR / f"{document_id}_{language}.mp4"
        )

        print("Document type:", document_type)
        print("Visual directory:", page_dir)
        print("First visual:", first_image_path)
        print("Scene count:", len(scenes))
        print("Audio scene count:", len(audio_scenes))

        # Render the final video.
        render_video(
            scene_plan,
            audio_plan,
            page_dir,
            subtitle_path,
            output_path
        )

        return {
            "status": "success",
            "document_id": document_id,
            "language": language,
            "document_type": document_type,
            "video_file": str(output_path),
            "subtitle_file": str(subtitle_path),
            "scene_count": len(scenes),
            "duration": round(total_duration, 3)
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
