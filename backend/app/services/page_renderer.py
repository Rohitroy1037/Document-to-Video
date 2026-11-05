import fitz
from pathlib import Path


def render_pdf_pages(pdf_path, output_dir):

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    document = fitz.open(pdf_path)

    page_images = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        output_path = (
            output_dir /
            f"page_{page_number}.png"
        )

        # Render PDF page at good quality
        matrix = fitz.Matrix(
            2,
            2
        )

        pixmap = page.get_pixmap(
            matrix=matrix,
            alpha=False
        )

        pixmap.save(
            str(output_path)
        )

        page_images.append(
            {
                "page_number": page_number,
                "image_path": str(output_path)
            }
        )

    document.close()

    return page_images