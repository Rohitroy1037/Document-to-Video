import os
import unittest

os.environ.setdefault("GROQ_API_KEY", "test-key")

from app.services.ai_analyzer import (
    _build_document_text,
    _parse_analysis_response,
)


class AiAnalyzerTests(unittest.TestCase):
    def test_document_excerpts_keep_all_page_numbers_with_bounded_text(self):
        content = [
            {"number": 2, "text": "a" * 2000},
            {"number": 5, "text": "b" * 2000},
        ]

        document_text = _build_document_text(content, max_chars=1000)

        self.assertIn("Section 2:", document_text)
        self.assertIn("Section 5:", document_text)
        self.assertIn("[page excerpt truncated]", document_text)
        self.assertLessEqual(
            sum(len(page.split("\n", 1)[1]) for page in document_text.split("\n\n")),
            1000,
        )

    def test_parses_valid_analysis(self):
        response = (
            '{"main_topic":"Topic","target_audience":"Readers",'
            '"summary":"Summary","important_sections":["Intro"],'
            '"key_points":[{"section":"Intro","points":["Point"]}]}'
        )

        analysis = _parse_analysis_response(response, "stop")

        self.assertEqual(analysis["main_topic"], "Topic")

    def test_reports_truncated_analysis_clearly(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            _parse_analysis_response('{"main_topic":"incomplete', "length")

    def test_rejects_malformed_analysis_json_clearly(self):
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            _parse_analysis_response('{"main_topic":"incomplete', "stop")
