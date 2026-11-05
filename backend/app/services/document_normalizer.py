def normalize_pdf(filename, pages):
    content = []

    for page in pages:
        content.append({
            "number": page["page_number"],
            "title": "",
            "text": page["text"]
        })

    return {
        "filename": filename,
        "document_type": "pdf",
        "content": content
    }


def normalize_pptx(filename, slides):
    content = []

    for slide in slides:
        text = slide["text"]

        lines = text.split("\n")

        title = lines[0] if lines else ""

        content.append({
            "number": slide["slide_number"],
            "title": title,
            "text": text
        })

    return {
        "filename": filename,
        "document_type": "pptx",
        "content": content
    }