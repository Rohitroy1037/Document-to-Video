
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import uuid
import json

from app.services.pdf_parser import extract_pdf_text
from app.services.ppt_parser import extract_ppt_text

from app.services.document_normalizer import (
    normalize_pdf,
    normalize_pptx
)

from app.services.page_renderer import render_pdf_pages
from app.services.pptx_renderer import render_pptx_slides


router = APIRouter()

UPLOAD_DIR = Path("storage/uploads")
DOCUMENT_DIR = Path("storage/documents")
PAGE_DIR = Path("storage/pages")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)
PAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    filename = file.filename

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing"
        )

    extension = Path(filename).suffix.lower()

    allowed_extensions = [".pdf", ".pptx"]

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and PPTX files are allowed"
        )

    document_id = str(uuid.uuid4())

    file_path = UPLOAD_DIR / f"{document_id}{extension}"

    try:
        content = await file.read()

        if not content:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )

        with open(file_path, "wb") as output_file:
            output_file.write(content)

        # --------------------------------
        # PDF processing
        # --------------------------------

        if extension == ".pdf":

            pages = extract_pdf_text(file_path)

            document = normalize_pdf(
                filename,
                pages
            )

            page_output_dir = (
                PAGE_DIR / document_id
            )

            render_pdf_pages(
                file_path,
                page_output_dir
            )

            visual_type = "pdf_pages"

        # --------------------------------
        # PPTX processing
        # --------------------------------

        else:

            slides = extract_ppt_text(
                file_path
            )

            document = normalize_pptx(
                filename,
                slides
            )

            slide_output_dir = (
                PAGE_DIR / document_id
            )

            rendered_slides = render_pptx_slides(
                file_path,
                slide_output_dir
            )

            if not rendered_slides:
                raise RuntimeError(
                    "No PPTX slides were rendered."
                )

            visual_type = "pptx_slides"

        # --------------------------------
        # Save normalized document
        # --------------------------------

        document["document_id"] = document_id

        document_path = (
            DOCUMENT_DIR /
            f"{document_id}.json"
        )

        with open(
            document_path,
            "w",
            encoding="utf-8"
        ) as output_file:

            json.dump(
                document,
                output_file,
                indent=2,
                ensure_ascii=False
            )

        return {
            "status": "success",
            "document_id": document_id,
            "filename": filename,
            "document_type": document["document_type"],
            "visual_type": visual_type,
            "visual_directory": str(
                PAGE_DIR / document_id
            ),
            "message": (
                "Document uploaded, processed, "
                "and visual assets generated successfully"
            )
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        await file.close()
