import os
import unittest

os.environ.setdefault("GROQ_API_KEY", "test-key")

from app.services.script_generator import _parse_script_response


class ScriptGeneratorTests(unittest.TestCase):
    def test_parses_valid_script_json(self):
        response = (
            '{"title":"Topic","introduction":"Intro",'
            '"sections":[{"section_title":"Part 1",'
            '"narration":"Details"}],"conclusion":"End"}'
        )

        script = _parse_script_response(response, "stop")

        self.assertEqual(script["title"], "Topic")
        self.assertEqual(script["sections"][0]["narration"], "Details")

    def test_parses_json_fenced_script(self):
        response = (
            '```json\n{"title":"Topic","introduction":"Intro",'
            '"sections":[],"conclusion":"End"}\n```'
        )

        script = _parse_script_response(response, "stop")

        self.assertEqual(script["title"], "Topic")

    def test_reports_truncated_response_clearly(self):
        with self.assertRaisesRegex(ValueError, "truncated"):
            _parse_script_response('{"title":"incomplete', "length")

    def test_rejects_malformed_json_with_clear_error(self):
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            _parse_script_response('{"title":"incomplete', "stop")
