from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
import json

from app.services.script_generator import generate_script
from app.utils.rate_limit import rate_limit


router = APIRouter()

ANALYSIS_DIR = Path("storage/analyses")
SCRIPT_DIR = Path("storage/scripts")

SCRIPT_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/script/{document_id}",
    dependencies=[Depends(rate_limit("generation", 30))],
)
async def generate_document_script(document_id: str):

    analysis_path = ANALYSIS_DIR / f"{document_id}.json"

    if not analysis_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Analysis not found. Run /analyze first."
        )

    try:

        with open(
            analysis_path,
            "r",
            encoding="utf-8"
        ) as input_file:

            analysis = json.load(input_file)

        script = generate_script(analysis)

        script_path = SCRIPT_DIR / f"{document_id}.json"

        with open(
            script_path,
            "w",
            encoding="utf-8"
        ) as output_file:

            json.dump(
                script,
                output_file,
                indent=2,
                ensure_ascii=False
            )

        return {
            "status": "success",
            "document_id": document_id,
            "script": script
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )