
from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

from app.services.scene_planner import create_scene_plan


router = APIRouter()

TRANSLATION_DIR = Path("storage/translations")
DOCUMENT_DIR = Path("storage/documents")
SCENE_DIR = Path("storage/scenes")

SCENE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


@router.post("/scenes/{document_id}/{language}")
async def create_scenes(
    document_id: str,
    language: str
):

    language = language.lower()

    translation_path = (
        TRANSLATION_DIR /
        f"{document_id}_{language}.json"
    )

    document_path = (
        DOCUMENT_DIR /
        f"{document_id}.json"
    )

    if not translation_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Translated script not found. "
                "Run /translate first."
            )
        )

    if not document_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    try:

        # Load translated narration script
        with open(
            translation_path,
            "r",
            encoding="utf-8"
        ) as input_file:

            script = json.load(input_file)

        # Load normalized source document
        with open(
            document_path,
            "r",
            encoding="utf-8"
        ) as input_file:

            document = json.load(input_file)

        # Generate AI scene plan
        scene_plan = create_scene_plan(
            script,
            document
        )

        # Preserve document type for the renderer
        document_type = document.get(
            "document_type",
            "pdf"
        )

        scene_plan["document_type"] = (
            document_type
        )

        # Save scene plan
        scene_path = (
            SCENE_DIR /
            f"{document_id}_{language}.json"
        )

        with open(
            scene_path,
            "w",
            encoding="utf-8"
        ) as output_file:

            json.dump(
                scene_plan,
                output_file,
                indent=2,
                ensure_ascii=False
            )

        return {
            "status": "success",
            "document_id": document_id,
            "language": language,
            "document_type": document_type,
            "scene_plan": scene_plan
        }

    except HTTPException:
        raise

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
