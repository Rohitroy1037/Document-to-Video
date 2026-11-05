import os
import json

from dotenv import load_dotenv
from groq import Groq


load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL_NAME = "openai/gpt-oss-20b"
MAX_COMPLETION_TOKENS = 3000


def _parse_script_response(result, finish_reason):
    if not result or not result.strip():
        raise ValueError("Groq returned an empty script response.")

    if finish_reason == "length":
        raise ValueError(
            "Groq truncated the narration script before completing it. "
            "Please try again."
        )

    result = result.strip()

    if result.startswith("```"):
        result = result.split("\n", 1)[-1]

    if result.endswith("```"):
        result = result[:-3]

    result = result.strip()

    try:
        script = json.loads(result)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Groq returned an invalid JSON narration script. "
            "Please try again."
        ) from error

    if not isinstance(script, dict):
        raise ValueError("The narration script must be a JSON object.")

    if not isinstance(script.get("title"), str):
        raise ValueError("The narration script is missing a valid title.")

    if not isinstance(script.get("introduction"), str):
        raise ValueError(
            "The narration script is missing a valid introduction."
        )

    if not isinstance(script.get("sections"), list):
        raise ValueError(
            "The narration script is missing its sections list."
        )

    if not isinstance(script.get("conclusion"), str):
        raise ValueError(
            "The narration script is missing a valid conclusion."
        )

    for index, section in enumerate(script["sections"], start=1):
        if not isinstance(section, dict):
            raise ValueError(f"Script section {index} must be an object.")
        if not isinstance(section.get("section_title"), str):
            raise ValueError(
                f"Script section {index} is missing a valid title."
            )
        if not isinstance(section.get("narration"), str):
            raise ValueError(
                f"Script section {index} is missing valid narration."
            )

    return script


def generate_script(analysis):

    prompt = f"""
You are a professional educational video script writer.

Create a clear and engaging narration script from the following
document analysis.

The script will be used to create an educational video.

Requirements:

1. Explain the topic in a logical order.
2. Use simple and natural language.
3. Do not add information that is not supported by the analysis.
4. Include an introduction.
5. Explain the important sections.
6. End with a short conclusion.
7. Make the narration suitable for spoken audio.
8. Avoid bullet points inside narration.
9. Return ONLY valid JSON.

Use exactly this structure:

{{
    "title": "",
    "introduction": "",
    "sections": [
        {{
            "section_title": "",
            "narration": ""
        }}
    ],
    "conclusion": ""
}}

Document analysis:

{json.dumps(analysis, indent=2)}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        reasoning_effort="low",
        include_reasoning=False,
        response_format={"type": "json_object"},
    )

    if not response.choices:
        raise ValueError("Groq returned no narration-script response.")

    choice = response.choices[0]
    return _parse_script_response(
        choice.message.content,
        choice.finish_reason,
    )