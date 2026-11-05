from pptx import Presentation

def extract_ppt_text(file_path):
    presentation = Presentation(file_path)

    slides = []

    for slide_number, slide in enumerate(presentation.slides, start=1):

        texts = []

        for shape in slide.shapes:

            if hasattr(shape, "text") and shape.text.strip():
                texts.append(shape.text.strip())

        slides.append({
            "slide_number": slide_number,
            "text": "\n".join(texts)
        })

    return slides