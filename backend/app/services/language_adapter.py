
import os
import time

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Check your backend .env file."
    )

client = Groq(api_key=api_key)

MODEL_NAME = "openai/gpt-oss-20b"
MAX_RETRIES = 3
MAX_COMPLETION_TOKENS = 2048


def translate_text(text, language, field_name):
    """
    Translate one field using low reasoning effort.
    """

    if not isinstance(text, str) or not text.strip():
        return text or ""

    prompt = f"""
Translate the following {field_name} into {language}.

Rules:
- Preserve the original meaning.
- Do not add or remove important information.
- Use natural language suitable for spoken narration.
- For Hinglish, use Roman Hindi mixed naturally with English.
- Keep technical terms where appropriate.
- Return only the translated text.
- Do not include explanations or Markdown.

Text:
{text}
"""

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.1,
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                reasoning_effort="low",
                include_reasoning=False,
            )

            if not response.choices:
                raise ValueError(
                    "Groq returned no response choices."
                )

            choice = response.choices[0]
            result = choice.message.content

            print(
                f"[Translation] Field={field_name}, "
                f"Attempt={attempt}, "
                f"Finish reason={choice.finish_reason}, "
                f"Content length={len(result or '')}"
            )

            if choice.finish_reason == "length":
                raise ValueError(
                    f"Groq reached the completion-token limit "
                    f"for '{field_name}'."
                )

            if not result or not result.strip():
                raise ValueError(
                    f"Groq returned empty content for '{field_name}'."
                )

            return result.strip()

        except Exception as error:
            last_error = error

            print(
                f"[Translation] Attempt {attempt} failed: {error}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(attempt)

    raise ValueError(
        f"Translation failed for '{field_name}' after "
        f"{MAX_RETRIES} attempts. Last error: {last_error}"
    )


def adapt_script_language(script, language):
    """
    Translate script fields individually and preserve JSON structure.
    """

    supported_languages = {
        "english",
        "hindi",
        "hinglish",
    }

    if not isinstance(language, str):
        raise ValueError("Language must be a string.")

    language = language.strip().lower()

    if language not in supported_languages:
        raise ValueError(
            "Supported languages: English, Hindi, Hinglish."
        )

    if not isinstance(script, dict):
        raise ValueError(
            "The input script must be a JSON object."
        )

    original_sections = script.get("sections", [])

    if not isinstance(original_sections, list):
        raise ValueError(
            "Script sections must be a list."
        )

    translated_script = {
        "title": translate_text(
            script.get("title", ""),
            language,
            "script title",
        ),
        "introduction": translate_text(
            script.get("introduction", ""),
            language,
            "introduction",
        ),
        "sections": [],
        "conclusion": translate_text(
            script.get("conclusion", ""),
            language,
            "conclusion",
        ),
    }

    for index, section in enumerate(
        original_sections,
        start=1,
    ):
        if not isinstance(section, dict):
            raise ValueError(
                f"Section {index} must be a JSON object."
            )

        translated_title = translate_text(
            section.get("section_title", ""),
            language,
            f"section {index} title",
        )

        translated_narration = translate_text(
            section.get("narration", ""),
            language,
            f"section {index} narration",
        )

        translated_script["sections"].append(
            {
                "section_title": translated_title,
                "narration": translated_narration,
            }
        )

    # Validate everything before the endpoint saves the result.
    if not translated_script["title"].strip():
        raise ValueError("Translated script title is empty.")

    for index, section in enumerate(
        translated_script["sections"],
        start=1,
    ):
        if not section["section_title"].strip():
            raise ValueError(
                f"Section {index} has an empty translated title."
            )

        if not section["narration"].strip():
            raise ValueError(
                f"Section {index} has empty translated narration."
            )

    return translated_script
