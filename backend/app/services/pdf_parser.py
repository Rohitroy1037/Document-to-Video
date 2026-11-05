import fitz

def extract_pdf_text(file_path):
    document = fitz.open(file_path)

    pages = []

    for page_number, page in enumerate(document, start = 1):
        text = page.get_text()

        pages.append({
            "page_number": page_number,
            "text": text.strip()
        })

    document.close()
    return pages