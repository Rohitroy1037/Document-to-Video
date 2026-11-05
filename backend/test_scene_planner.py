import os
import unittest

os.environ.setdefault("GROQ_API_KEY", "test-key")

from app.services.scene_planner import _build_page_context


class ScenePlannerTests(unittest.TestCase):
    def test_page_context_keeps_page_numbers_with_bounded_text(self):
        document_content = [
            {"number": 2, "title": "First page", "text": "a" * 2000},
            {"number": 5, "title": "Second page", "text": "b" * 2000},
        ]

        page_context = _build_page_context(
            document_content,
            max_text_chars=1000,
        )

        self.assertEqual(
            [page["source_page"] for page in page_context],
            [2, 5],
        )
        self.assertLessEqual(
            sum(len(page["text"]) for page in page_context),
            1000,
        )
        self.assertTrue(
            all("page excerpt truncated" in page["text"] for page in page_context)
        )
