from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path
import json

from app.services.language_adapter import adapt_script_language
from app.utils.rate_limit import rate_limit


router = APIRouter()

SCRIPT_DIR = Path("storage/scripts")
TRANSLATION_DIR = Path("storage/translations")

TRANSLATION_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/translate/{document_id}/{language}",
    dependencies=[Depends(rate_limit("generation", 30))],
)
async def translate_script(document_id: str, language: str):

    script_path = SCRIPT_DIR / f"{document_id}.json"

    if not script_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Script not found. Run /script first."
        )

    try:

        with open(
            script_path,
            "r",
            encoding="utf-8"
        ) as input_file:

            script = json.load(input_file)

        translated_script = adapt_script_language(
            script,
            language
        )

        translation_path = (
            TRANSLATION_DIR /
            f"{document_id}_{language.lower()}.json"
        )

        with open(
            translation_path,
            "w",
            encoding="utf-8"
        ) as output_file:

            json.dump(
                translated_script,
                output_file,
                indent=2,
                ensure_ascii=False
            )

        return {
            "status": "success",
            "document_id": document_id,
            "language": language,
            "script": translated_script
        }

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )