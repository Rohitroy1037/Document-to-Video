import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL_NAME = "openai/gpt-oss-20b"
MAX_DOCUMENT_CHARS = 10000
MAX_PROMPT_BYTES = 14000
MAX_COMPLETION_TOKENS = 2500


def _build_document_text(content, max_chars=MAX_DOCUMENT_CHARS):
    page_count = len(content)
    page_text_budget = min(
        1600,
        max_chars // page_count if page_count else 0
    )
    sections = []

    for index, item in enumerate(content, start=1):
        page_number = item.get("number", index)
        text = str(item.get("text", ""))

        if len(text) > page_text_budget:
            marker = " ... [page excerpt truncated] ... "
            if page_text_budget <= len(marker):
                text = text[:page_text_budget]
            else:
                content_budget = page_text_budget - len(marker)
                first_part = content_budget // 2
                last_part = content_budget - first_part
                text = (
                    text[:first_part]
                    + marker
                    + (text[-last_part:] if last_part else "")
                )

        sections.append(f"Section {page_number}:\n{text}")

    return "\n\n".join(sections)


def _parse_analysis_response(result, finish_reason):
    if not result or not result.strip():
        raise ValueError("Groq returned an empty document analysis.")

    if finish_reason == "length":
        raise ValueError(
            "Groq truncated the document analysis before completing it. "
            "Please try again."
        )

    try:
        analysis = json.loads(result)
    except json.JSONDecodeError as error:
        raise ValueError(
            "Groq returned invalid JSON for document analysis. "
            "Please try again."
        ) from error

    if not isinstance(analysis, dict):
        raise ValueError("Document analysis must be a JSON object.")

    for field in ("main_topic", "target_audience", "summary"):
        if not isinstance(analysis.get(field), str):
            raise ValueError(
                f"Document analysis is missing a valid '{field}' field."
            )

    if not isinstance(analysis.get("important_sections"), list):
        raise ValueError(
            "Document analysis is missing its important_sections list."
        )

    if not isinstance(analysis.get("key_points"), list):
        raise ValueError(
            "Document analysis is missing its key_points list."
        )

    return analysis


def analyze_document(document):

    content = document["content"]

    if not isinstance(content, list) or not content:
        raise ValueError("Document contains no pages or slides to analyze.")

    document_text = _build_document_text(content)

    prompt = f"""
You are a document analysis assistant.

Analyze the following document excerpts. They cover every page/slide,
but long page text may be shortened.

Identify:

1. Main topic
2. Target audience
3. Overall summary
4. Important sections
5. Key points from each section

Return ONLY valid JSON.

Use exactly this structure:

{{
    "main_topic": "",
    "target_audience": "",
    "summary": "",
    "important_sections": [],
    "key_points": []
}}

Document:

{document_text}
"""

    while len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        document_text = _build_document_text(
            content,
            max_chars=max(
                0,
                MAX_DOCUMENT_CHARS
                - (len(prompt.encode("utf-8")) - MAX_PROMPT_BYTES)
                - 100
            )
        )
        prompt = f"""
You are a document analysis assistant.

Analyze the following document excerpts. They cover every page/slide,
but long page text may be shortened.

Identify:

1. Main topic
2. Target audience
3. Overall summary
4. Important sections
5. Key points from each section

Return ONLY valid JSON.

Use exactly this structure:

{{
    "main_topic": "",
    "target_audience": "",
    "summary": "",
    "important_sections": [],
    "key_points": []
}}

Document:

{document_text}
"""

        if not document_text and len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError(
                "Document metadata is too large to fit within the "
                "analysis request limit."
            )

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        reasoning_effort="low",
        include_reasoning=False,
        response_format={"type": "json_object"},
    )

    if not response.choices:
        raise ValueError("Groq returned no document-analysis response.")

    choice = response.choices[0]
    return _parse_analysis_response(
        choice.message.content,
        choice.finish_reason,
    )