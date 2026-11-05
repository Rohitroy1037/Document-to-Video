import os
import unittest

os.environ.setdefault("GROQ_API_KEY", "test-key")

from app.services.document_chat import (
    _chunk_document_pages,
    _cosine_similarity,
    _strip_model_page_citations,
)


class DocumentChatTests(unittest.TestCase):
    def test_chunks_keep_source_pages_and_overlap(self):
        content = [
            {"number": 3, "title": "", "text": "0123456789" * 10},
            {"number": 7, "title": "", "text": "b" * 100},
        ]

        chunks = _chunk_document_pages(
            content,
            chunk_size=60,
            overlap=10,
        )

        self.assertEqual({chunk["page"] for chunk in chunks}, {3, 7})
        page_three_chunks = [chunk["text"] for chunk in chunks if chunk["page"] == 3]
        self.assertEqual(page_three_chunks[0][-10:], page_three_chunks[1][:10])

    def test_cosine_similarity_ranks_matching_vectors(self):
        self.assertAlmostEqual(
            _cosine_similarity([1.0, 0.0], [1.0, 0.0]),
            1.0,
        )
        self.assertAlmostEqual(
            _cosine_similarity([1.0, 0.0], [0.0, 1.0]),
            0.0,
        )

    def test_cosine_similarity_handles_zero_vectors(self):
        self.assertEqual(_cosine_similarity([0.0, 0.0], [1.0, 0.0]), 0.0)

    def test_removes_unverified_model_page_citations(self):
        answer = "The proposal predicts release risk. [Page\u202f9]"

        self.assertEqual(
            _strip_model_page_citations(answer),
            "The proposal predicts release risk.",
        )
