import json
import asyncio
from config import Config, get_genai_client
from google.genai import types
from models.schemas import CourseOutline


def clean_json_string(raw_text: str) -> str:
    if not raw_text:
        return ""
    text = raw_text.strip()
    if text.startswith("```"):
        newline_idx = text.find("\n")
        if newline_idx != -1:
            text = text[newline_idx:].strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


async def generate_course_design(
    params: dict, source_text: str
) -> tuple[CourseOutline, str]:
    """
    Call 1 — Design the course outline.

    When source_text is provided, also instructs the LLM to produce a
    'compressed_source': a 3-paragraph, 400-600 word prose distillation of
    the uploaded document.  This compressed version is returned alongside the
    outline and passed into Call 2 so the content writer has faithful source
    context without re-sending thousands of raw tokens.

    Returns: (CourseOutline, compressed_source_str)
    compressed_source_str is "" when no source document was uploaded.
    """
    duration_str = params.get('duration', '')

    if "Quick Bite" in duration_str:
        module_constraint = "Strictly 1 module"
        lesson_constraint = "Strictly 3 lessons"
    elif "Deep Dive" in duration_str:
        module_constraint = "Strictly 5 modules"
        lesson_constraint = "Strictly 3 lessons per module"
    else:
        module_constraint = "Strictly 3 modules"
        lesson_constraint = "Strictly 3 lessons per module"

    has_source = bool(source_text and source_text.strip())

    # ── Base JSON schema ──────────────────────────────────────────────────────
    schema_example = """{
  "title": "Course Title",
  "description": "Detailed course description...",
  "total_modules": 5,
  "modules": [
    {
      "index": 1,
      "title": "Module Title",
      "learning_objectives": ["Objective 1", "Objective 2"],
      "lessons": [
        {
          "index": 1,
          "title": "Lesson Title"
        }
      ]
    }
  ]"""

    if has_source:
        schema_example += """,
  "compressed_source": "Paragraph 1 — 2-3 sentences covering the core domain, subject matter, and purpose of the source document.\\n\\nParagraph 2 — 3-4 sentences covering the key concepts, terminology, frameworks, and mechanisms explained in the source.\\n\\nParagraph 3 — 2-3 sentences covering specific examples, data points, case studies, or real-world applications found in the source."
}"""
    else:
        schema_example += "\n}"

    # ── System prompt ─────────────────────────────────────────────────────────
    system_prompt = f"""You are an expert instructional designer.
Your task is to create a structured course outline based on the user's prompt and optional source document.
You MUST output valid JSON matching the exact structure below:

{schema_example}

CRITICAL CONSTRAINTS:
1. Generate {module_constraint}.
2. Generate {lesson_constraint}.
3. You MUST fully populate all required fields, including 'description' and the 'modules' array. Do not omit any fields or leave arrays empty."""

    if has_source:
        system_prompt += """

COMPRESSION TASK — you MUST also populate the 'compressed_source' field:
Write a faithful 3-paragraph prose distillation of the source document, totalling 400-600 words.
- Paragraph 1: The core domain, subject matter, and purpose of the source.
- Paragraph 2: Key concepts, terminology, frameworks, and mechanisms — explained in connected sentences.
- Paragraph 3: Specific examples, data points, case studies, or domain-specific applications from the source.
Rules:
  • Write in flowing prose, NOT bullet points or lists.
  • Preserve accuracy — do not invent or extrapolate facts not in the source.
  • Optimise for a content writer who needs rich domain context to write educational slides and essays.
  • Separate the three paragraphs with \\n\\n."""

    # ── User prompt ───────────────────────────────────────────────────────────
    prompt = f"""
    Course Parameters:
    - Topic/Prompt: {params.get('prompt')}
    - Target Audience: {params.get('audience', 'General')}
    - Blueprint: {params.get('blueprint')}
    - Duration: {params.get('duration')}
    - Level: {params.get('level')}
    - Tone: {params.get('tone')}
    """
    if has_source:
        prompt += f"\n\nSource Material (Base your course on this):\n{source_text}"

    client = get_genai_client()

    for attempt in range(3):
        print(f"\n[generate_course_design] Sending request to Gemini (Attempt {attempt+1})...")
        try:
            response = await client.aio.models.generate_content_stream(
                model=Config.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.32,
                    response_mime_type="application/json"
                )
            )
            text = ""
            async for chunk in response:
                try:
                    if chunk.text:
                        print(chunk.text, end="", flush=True)
                        text += chunk.text
                except ValueError:
                    pass
            print("\n[generate_course_design] Finished receiving response.")

            if not text or not text.strip():
                raise Exception("Generative API returned an empty response.")

            cleaned = clean_json_string(text)
            raw_data = json.loads(cleaned)

            # Extract compressed_source before building the Pydantic model
            # (CourseOutline has no such field — would fail validation if left in)
            compressed_source = ""
            if has_source:
                raw_compressed = raw_data.pop("compressed_source", "")
                if isinstance(raw_compressed, str):
                    compressed_source = raw_compressed.strip()
                    word_count = len(compressed_source.split())
                    print(f"[generate_course_design] ✓ compressed_source: {word_count} words, "
                          f"{len(compressed_source.splitlines())} lines.")
                else:
                    print("[generate_course_design] ⚠ compressed_source missing or wrong type — continuing without it.")

            outline = CourseOutline(**raw_data)
            return outline, compressed_source

        except Exception as e:
            print(f"[generate_course_design] Attempt {attempt+1} failed: {str(e)}")
            if attempt == 2:
                raise Exception(
                    f"Failed to generate course design after 3 attempts. Last error: {str(e)}"
                )
            await asyncio.sleep(1)
