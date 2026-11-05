import tempfile
import unittest
from pathlib import Path

import fitz

from app.services.pdf_parser import extract_pdf_text


class PdfParserTests(unittest.TestCase):
    def test_extracts_text_from_every_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "multipage.pdf"
            document = fitz.open()

            for page_number in range(1, 4):
                page = document.new_page()
                page.insert_text((72, 72), f"Page {page_number}")

            document.save(pdf_path)
            document.close()

            pages = extract_pdf_text(pdf_path)

        self.assertEqual(
            [page["page_number"] for page in pages],
            [1, 2, 3],
        )
        self.assertEqual(
            [page["text"] for page in pages],
            ["Page 1", "Page 2", "Page 3"],
        )
