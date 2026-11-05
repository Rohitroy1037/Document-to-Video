# ```python
import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MAX_DOCUMENT_CONTEXT_CHARS = 4000
MAX_PROMPT_BYTES = 14000
MAX_COMPLETION_TOKENS = 4000


def _build_page_context(document_content, max_text_chars):
    page_count = len(document_content)
    page_text_budget = min(
        1200,
        max_text_chars // page_count if page_count else 0
    )
    page_context = []

    for index, page in enumerate(document_content, start=1):
        page_number = int(page.get("number", index))
        title = str(page.get("title", ""))[:200]
        text = str(page.get("text", ""))

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

        page_context.append({
            "source_page": page_number,
            "title": title,
            "text": text
        })

    return page_context


def _build_scene_prompt(script, page_context, total_pages):
    return f"""
You are a professional educational video scene planner.

Create a scene plan for the narration script using the original
document. The original document contains {total_pages} pages/slides.

Return ONLY valid JSON in this format:

{{
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Introduction",
      "narration": "Exact narration text",
      "visual_description": "Describe the relevant visual",
      "source_page": 1,
      "duration": 10,
      "visual_type": "document_focus",
      "animation": "zoom_in"
    }}
  ]
}}

STRICT RULES:

1. Return one valid JSON object only.
2. Preserve the narration wording exactly as provided.
3. Do not invent facts or add unsupported information.
4. Create exactly one scene for the introduction, one for each
   script section, and one for the conclusion. Do not split them.
5. Every scene must have a valid source_page.
6. source_page must refer to the original page number given below.
7. Cover content from EVERY page that contains relevant content.
8. Do not assign every scene to page 1 by default.
9. If narration discusses content from page 2, assign source_page 2.
10. Assign each scene to the page most relevant to its narration.
11. Do not create narration that is absent from the provided script.
12. duration must be a positive number in seconds.
13. visual_type must be one of:
    document_focus, title, key_points, conclusion, static
14. animation must be one of:
    zoom_in, zoom_out, pan_left, pan_right, static
15. Use zoom_in for introductions.
16. Use zoom_in or pan_left for explanations.
17. Use pan_right or zoom_in for key points.
18. Use zoom_out for conclusions.
19. Keep visual descriptions simple and relevant.
20. Use scene_number values starting from 1 in order.
21. Ensure all JSON strings are correctly escaped.
22. If a page contains no content relevant to the narration,
    do not invent narration just to include that page.
23. Page text may be excerpted; use its page number and available
    content to select the most relevant source page.
24. Keep titles and visual descriptions to a few words.

NARRATION SCRIPT:
{json.dumps(script, ensure_ascii=False)}

ORIGINAL DOCUMENT PAGE BY PAGE:
{json.dumps(page_context, ensure_ascii=False)}
"""


def create_scene_plan(script, document):
    document_content = document.get("content", [])

    total_pages = len(document_content)
    print("Total PDF pages:", total_pages)

    if not document_content:
        raise ValueError("Document contains no pages or slides.")

    total_pages = len(document_content)

    page_text_budget = MAX_DOCUMENT_CONTEXT_CHARS
    page_context = _build_page_context(
        document_content,
        page_text_budget
    )
    prompt = _build_scene_prompt(script, page_context, total_pages)

    while len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES and page_text_budget:
        page_text_budget = max(
            0,
            page_text_budget
            - (len(prompt.encode("utf-8")) - MAX_PROMPT_BYTES)
            - 100
        )
        page_context = _build_page_context(
            document_content,
            page_text_budget
        )
        prompt = _build_scene_prompt(script, page_context, total_pages)

    if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ValueError(
            "Narration is too long to fit within the scene-planning "
            "request limit. Shorten the script and try again."
        )

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        reasoning_effort="low",
        include_reasoning=False,
        response_format={"type": "json_object"},
    )

    if not response.choices:
        raise ValueError("Groq returned no scene-planning response.")

    choice = response.choices[0]
    result = choice.message.content

    print("Scene planning finish reason:", choice.finish_reason)

    if choice.finish_reason == "length":
        raise ValueError(
            "Groq truncated the scene plan before completing it. "
            "Please try again."
        )

    if not result or not result.strip():
        raise ValueError("Groq returned an empty scene-planning response.")

    result = result.strip()

    # Remove optional Markdown fences.
    result = re.sub(
        r"^```(?:json)?\s*",
        "",
        result,
        flags=re.IGNORECASE
    )
    result = re.sub(r"\s*```$", "", result).strip()

    # Extract the JSON object if extra text appears before it.
    if not result.startswith("{"):
        start = result.find("{")
        if start != -1:
            result = result[start:]

    try:
        scene_plan = json.loads(result)
    except json.JSONDecodeError as error:
        print("Invalid scene-planning response:")
        print(repr(result[:2000]))

        raise ValueError(
            "AI returned invalid JSON for scene planning. "
            f"JSON error: {error}. "
            f"Finish reason: {choice.finish_reason}"
        ) from error

    if not isinstance(scene_plan, dict):
        raise ValueError("Scene plan must be a JSON object.")

    scenes = scene_plan.get("scenes")

    if not isinstance(scenes, list) or not scenes:
        raise ValueError(
            "Scene plan must contain a non-empty scenes list."
        )

    allowed_visual_types = {
        "document_focus",
        "title",
        "key_points",
        "conclusion",
        "static"
    }

    allowed_animations = {
        "zoom_in",
        "zoom_out",
        "pan_left",
        "pan_right",
        "static"
    }

    required_fields = [
        "title",
        "narration",
        "visual_description",
        "source_page",
        "duration",
        "visual_type",
        "animation"
    ]

    valid_page_numbers = {
        int(page.get("number", index))
        for index, page in enumerate(document_content, start=1)
    }

    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {index} must be a JSON object.")

        for field in required_fields:
            if field not in scene:
                raise ValueError(
                    f"Field '{field}' missing in scene {index}."
                )

        scene["scene_number"] = index

        try:
            source_page = int(scene["source_page"])
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid source_page in scene {index}."
            )

        if source_page not in valid_page_numbers:
            raise ValueError(
                f"Scene {index} refers to page {source_page}, "
                f"which does not exist in the document."
            )

        scene["source_page"] = source_page

        try:
            duration = float(scene["duration"])
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid duration in scene {index}."
            )

        if duration <= 0:
            raise ValueError(
                f"Duration must be positive in scene {index}."
            )

        scene["duration"] = duration

        if scene["visual_type"] not in allowed_visual_types:
            raise ValueError(
                f"Invalid visual_type in scene {index}: "
                f"{scene['visual_type']}"
            )

        if scene["animation"] not in allowed_animations:
            raise ValueError(
                f"Invalid animation in scene {index}: "
                f"{scene['animation']}"
            )

        if not isinstance(scene["narration"], str):
            raise ValueError(
                f"Narration must be text in scene {index}."
            )

    # Log page coverage for debugging.
    covered_pages = sorted({
        scene["source_page"] for scene in scenes
    })

    print("Total document pages/slides:", total_pages)
    print("Pages referenced by scenes:", covered_pages)

    scene_plan["scenes"] = scenes
    return scene_plan
