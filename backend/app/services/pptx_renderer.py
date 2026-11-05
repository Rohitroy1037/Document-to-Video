import subprocess
import os
import shutil
from pathlib import Path
import fitz


LIBREOFFICE_PATH = (
    os.getenv("LIBREOFFICE_PATH")
    or shutil.which("soffice")
    or r"C:\Program Files\LibreOffice\program\soffice.exe"
)


def render_pptx_slides(
    pptx_path,
    output_dir
):
    pptx_path = Path(pptx_path).resolve()
    output_dir = Path(output_dir).resolve()

    if not pptx_path.exists():
        raise FileNotFoundError(
            f"PPTX file not found: {pptx_path}"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Temporary directory for PDF conversion
    pdf_dir = output_dir / "temp_pdf"

    pdf_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Convert PPTX to PDF using LibreOffice
    command = [
        LIBREOFFICE_PATH,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(pdf_dir),
        str(pptx_path)
    ]

    subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=120
    )

    pdf_path = (
        pdf_dir /
        f"{pptx_path.stem}.pdf"
    )

    if not pdf_path.exists():
        raise RuntimeError(
            "LibreOffice did not generate the PDF."
        )

    # Render every PDF page as a slide image
    document = fitz.open(pdf_path)

    rendered_slides = []

    try:
        for slide_number, page in enumerate(
            document,
            start=1
        ):
            image_path = (
                output_dir /
                f"slide_{slide_number}.png"
            )

            # Render at 2x resolution
            matrix = fitz.Matrix(2, 2)

            pixmap = page.get_pixmap(
                matrix=matrix,
                alpha=False
            )

            pixmap.save(
                str(image_path)
            )

            rendered_slides.append({
                "slide_number": slide_number,
                "image_path": str(image_path)
            })

    finally:
        document.close()

    return rendered_slides