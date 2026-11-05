from fastapi import APIRouter, HTTPException
from pathlib import Path
import json

from app.services.ai_analyzer import analyze_document


router = APIRouter()

DOCUMENT_DIR = Path("storage/documents")
ANALYSIS_DIR = Path("storage/analyses")

ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/analyze/{document_id}")
async def analyze(document_id: str):

    document_path = DOCUMENT_DIR / f"{document_id}.json"

    if not document_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    try:

        with open(document_path, "r", encoding="utf-8") as input_file:
            document = json.load(input_file)

        analysis = analyze_document(document)

        analysis_path = ANALYSIS_DIR / f"{document_id}.json"

        with open(
            analysis_path,
            "w",
            encoding="utf-8"
        ) as output_file:

            json.dump(
                analysis,
                output_file,
                indent=2,
                ensure_ascii=False
            )

        return {
            "status": "success",
            "document_id": document_id,
            "analysis": analysis
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )