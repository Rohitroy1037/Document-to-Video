from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
from starlette.concurrency import run_in_threadpool

import json

from app.services.video_renderer import render_video
from app.services.subtitle_generator import create_subtitle_file
from app.utils.rate_limit import rate_limit


router = APIRouter()


# =========================================================
# STORAGE DIRECTORIES
# =========================================================

AUDIO_PLAN_DIR = Path("storage/audio")
SCENE_DIR = Path("storage/scenes")
DOCUMENT_DIR = Path("storage/documents")
PAGE_DIR = Path("storage/pages")

VIDEO_DIR = Path("storage/videos")
SUBTITLE_DIR = Path("storage/subtitles")


for directory in [VIDEO_DIR, SUBTITLE_DIR]:

    directory.mkdir(
        parents=True,
        exist_ok=True
    )


# =========================================================
# CREATE VIDEO ENDPOINT
# =========================================================

@router.post(
    "/video/{document_id}/{language}",
    dependencies=[
        Depends(rate_limit("generation", 30))
    ],
)
async def create_video(
    document_id: str,
    language: str
):

    language = language.lower()

    # -----------------------------------------------------
    # File paths
    # -----------------------------------------------------

    scene_path = (
        SCENE_DIR
        / f"{document_id}_{language}.json"
    )

    audio_plan_path = (
        AUDIO_PLAN_DIR
        / f"scenes_{document_id}_{language}"
        / "audio_plan.json"
    )

    document_path = (
        DOCUMENT_DIR
        / f"{document_id}.json"
    )

    page_dir = (
        PAGE_DIR
        / document_id
    )

    subtitle_path = (
        SUBTITLE_DIR
        / f"{document_id}_{language}.srt"
    )

    output_path = (
        VIDEO_DIR
        / f"{document_id}_{language}.mp4"
    )

    # =====================================================
    # STEP 1: CHECK REQUIRED FILES
    # =====================================================

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
            detail=(
                "Document visuals directory not found: "
                f"{page_dir}"
            )
        )

    try:

        # =================================================
        # STEP 2: LOAD SCENE PLAN
        # =================================================

        with open(
            scene_path,
            "r",
            encoding="utf-8"
        ) as file:

            scene_plan = json.load(file)

        # =================================================
        # STEP 3: LOAD AUDIO PLAN
        # =================================================

        with open(
            audio_plan_path,
            "r",
            encoding="utf-8"
        ) as file:

            audio_plan = json.load(file)

        # =================================================
        # STEP 4: LOAD DOCUMENT METADATA
        # =================================================

        with open(
            document_path,
            "r",
            encoding="utf-8"
        ) as file:

            document = json.load(file)

        document_type = str(
            document.get("document_type", "")
        ).lower()

        if document_type not in {"pdf", "pptx"}:

            raise ValueError(
                f"Unsupported document type: {document_type}"
            )

        # Pass document type to renderer.
        scene_plan["document_type"] = document_type

        # =================================================
        # STEP 5: GET SCENES
        # =================================================

        scenes = scene_plan.get(
            "scenes",
            []
        )

        audio_scenes = audio_plan.get(
            "scenes",
            []
        )

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

        # =================================================
        # STEP 6: CHECK DOCUMENT VISUALS
        # =================================================

        first_image_name = (
            "slide_1.png"
            if document_type == "pptx"
            else "page_1.png"
        )

        first_image_path = (
            page_dir
            / first_image_name
        )

        if not first_image_path.exists():

            raise FileNotFoundError(
                f"Expected {document_type.upper()} "
                f"visual not found: {first_image_path}"
            )

        # =================================================
        # STEP 7: MATCH AUDIO WITH SCENES
        # =================================================

        audio_map = {}

        for item in audio_scenes:

            if "scene_number" not in item:

                raise ValueError(
                    "Audio plan contains an entry "
                    "without scene_number."
                )

            audio_map[
                int(item["scene_number"])
            ] = item

        # =================================================
        # STEP 8: UPDATE SCENE DURATIONS
        # =================================================

        subtitle_scene_plan = {
            "scenes": []
        }

        total_duration = 0.0

        for index, scene in enumerate(
            scenes,
            start=1
        ):

            scene_number = int(
                scene.get(
                    "scene_number",
                    index
                )
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

        # =================================================
        # STEP 9: GENERATE SUBTITLES
        # =================================================

        create_subtitle_file(
            subtitle_scene_plan,
            subtitle_path
        )

        # =================================================
        # STEP 10: LOG RENDERING INFORMATION
        # =================================================

        print("\n" + "=" * 55, flush=True)

        print(
            "STARTING FINAL VIDEO GENERATION",
            flush=True
        )

        print(
            "Document ID:",
            document_id,
            flush=True
        )

        print(
            "Language:",
            language,
            flush=True
        )

        print(
            "Document type:",
            document_type,
            flush=True
        )

        print(
            "Visual directory:",
            page_dir,
            flush=True
        )

        print(
            "Scene count:",
            len(scenes),
            flush=True
        )

        print(
            "Audio scene count:",
            len(audio_scenes),
            flush=True
        )

        print(
            "Expected duration:",
            round(total_duration, 2),
            "seconds",
            flush=True
        )

        print("=" * 55, flush=True)

        # =================================================
        # STEP 11: RENDER FINAL VIDEO
        # =================================================

        # Run CPU-intensive synchronous rendering in a
        # worker thread instead of blocking the event loop.

        render_result = await run_in_threadpool(
            render_video,
            scene_plan,
            audio_plan,
            page_dir,
            subtitle_path,
            output_path
        )

        # =================================================
        # STEP 12: RETURN RESPONSE
        # =================================================

        return {

            "status": "success",

            "message": "Video generated successfully.",

            "document_id": document_id,

            "language": language,

            "document_type": document_type,

            "video_file": str(output_path),

            "subtitle_file": str(subtitle_path),

            "scene_count": len(scenes),

            "duration": round(total_duration, 3),

            "rendering_time": render_result.get(
                "rendering_time"
            )

        }

    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except HTTPException:

        raise

    except Exception as error:

        print(
            "VIDEO GENERATION ERROR:",
            str(error),
            flush=True
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )