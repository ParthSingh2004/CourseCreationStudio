import json
import asyncio
from config import Config, get_genai_client
from google.genai import types
from models.schemas import (
    FullCourseContent, CourseOutline, ModuleStub, LessonContent, LessonSegment,
    Quiz, FlashcardDeck, TableData, QuizQuestion, Flashcard
)


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


def _build_schema_and_system_prompt(
    include_audio: bool,
    include_quizzes: bool,
    include_flashcards: bool,
) -> tuple[str, str]:
    """
    Returns (expected_schema_str, system_prompt_str) for a *single module*.
    Keeping the schema tight — one module at a time — so the output never
    exceeds the token limit regardless of how many modules exist.
    """
    # ── JSON Schema ───────────────────────────────────────────────────────────
    expected_schema = """{
  "lessons": [
    {
      "module_index": 1,
      "lesson_index": 1,
      "title": "Lesson Title",
      "segments": [
        {
          "slide_index": 1,
          "slide_type": "text",
          "slide_title": "Slide Title",
          "slide_bullets": ["Each bullet must be a full explanatory sentence of 20-30 words that teaches the concept clearly, not just a label or keyword.", "A second sentence that provides context, an example, or expands on why this concept matters to the learner."]"""

    if include_audio:
        expected_schema += ',\n          "narration": "Natural spoken explanation of this slide content in 3-4 sentences"'

    expected_schema += """
        },
        {
          "slide_index": 2,
          "slide_type": "photo",
          "slide_title": "Overview of the Topic",
          "slide_bullets": ["A short contextual sentence to accompany the visual."],
          "image_query": "students learning classroom" """

    if include_audio:
        expected_schema += ',\n          "narration": "Narration for the photo slide."'

    expected_schema += """
        },
        {
          "slide_index": 3,
          "slide_type": "table",
          "slide_title": "Comparison of Approaches",
          "slide_bullets": [],
          "table_data": {
            "headers": ["Approach", "Pros", "Cons"],
            "rows": [
              ["Method A", "Fast and scalable", "Requires large datasets"],
              ["Method B", "Works on small data", "Slower inference time"]
            ]
          }"""

    if include_audio:
        expected_schema += ',\n          "narration": "Narration for the table slide."'

    expected_schema += """
        }
      ],
      "key_takeaways": ["Takeaway as a complete sentence of 15-20 words summarising the most important insight."],
      "lesson_essay": "A rich, flowing educational essay of 150-200 words that expands on everything covered in this lesson. Write in continuous prose paragraphs — not bullet points. Explain the key concepts in depth, give concrete real-world examples, show why the topic matters, and connect ideas across the slides. Match the course tone and level."
    }
  ]"""

    if include_quizzes:
        expected_schema += """,
  "quiz": {
    "module_index": 1,
    "questions": [
      {
        "question": "Question text?",
        "options": ["Opt A", "Opt B", "Opt C", "Opt D"],
        "correct_index": 0,
        "explanation": "Why correct..."
      }
    ]
  }"""

    if include_flashcards:
        expected_schema += """,
  "flashcard_deck": {
    "module_index": 1,
    "cards": [
      {
        "front": "Term",
        "back": "Definition"
      }
    ]
  }"""

    expected_schema += "\n}"

    # ── System Prompt ─────────────────────────────────────────────────────────
    SYSTEM_PROMPT = f"""You are an expert instructional designer and curriculum writer.
Your task is to write the COMPLETE content for ONE MODULE of a course based on the provided Module Outline.
You will generate lessons, slides, bullet points, and optionally narrations, a quiz, and a flashcard deck.

CRITICAL INSTRUCTIONS:
1. Generate exactly the number of lessons specified in the module outline.
2. For each lesson, generate exactly 3 slide segments.
3. BULLET POINTS ARE THE MOST IMPORTANT PART. Each bullet point in 'slide_bullets' MUST be a full, informative sentence of 20-30 words. Do NOT write single-word labels, short fragments, or vague phrases. Each bullet should explain a concept, provide context, or give an example. Aim for 3-4 bullets per slide (except table slides, which may have empty slide_bullets).
4. Key takeaways must also be complete sentences of 15-20 words summarising the most important insight from the lesson.
4b. LESSON ESSAY — Every lesson MUST include a 'lesson_essay' field: a rich, continuous prose essay of 150-200 words. Rules:
    - Write in flowing paragraphs, NOT bullet points or lists.
    - Expand in depth on all 3 slides of the lesson — explain the concepts, give real-world examples, show why they matter.
    - Match the course tone (formal, conversational, etc.) and difficulty level.
    - Do NOT repeat the slide titles or bullets verbatim; synthesise and deepen them.
    - This is the learner's primary reading material — make it genuinely educational.
5. SLIDE TYPES — every segment MUST include a 'slide_type' field. Choose wisely:
   - "text" (DEFAULT): Use for most slides. Include 3-4 bullet points.
   - "photo": Use ONLY ONCE PER MODULE — on the very first slide of the module's first lesson — to set an opening visual context. For all other lessons, default to "text".
     PHOTO RULES:
     • The 'image_query' MUST be a concrete, photogenic search term of 2-4 words that returns real stock photographs on Unsplash.
     • Unsplash is a PHOTOGRAPHY site — it has photos of people, workplaces, physical objects, and environments. It does NOT have diagrams, charts, code screenshots, or abstract technical illustrations.
     • GOOD queries (concrete, visual): "students studying together", "data scientist laptop", "medical professional hospital", "financial charts desk", "team meeting whiteboard", "software engineer coding", "laboratory research scientist"
     • BAD queries (abstract, technical, will return irrelevant photos): "neural network diagram", "binary tree structure", "machine learning algorithm", "blockchain nodes", "sql database schema"
     • Rule of thumb: if you cannot picture a photographer physically taking a photo of it, do NOT use it as an image_query. Translate the topic into the HUMAN CONTEXT around it instead.
     • slide_bullets can have 1-2 short contextual sentences.
   - "table": Use ONLY when the content is genuinely comparative (e.g., comparing two algorithms, listing pros and cons across options). Include a 'table_data' field with headers and rows. Rows must have the same number of cells as headers. slide_bullets should be empty [].
   RULE: Each module may have at most 1 "photo" slide total. At least 1 slide per lesson must be "text". At most 1 "table" slide per lesson.
"""
    if include_audio:
        SYSTEM_PROMPT += "6. Since 'audio' was requested, you MUST include a 'narration' script for EVERY slide. Write it as a natural spoken explanation of 3-4 sentences.\n"
    if include_quizzes:
        SYSTEM_PROMPT += f"7. Since 'quizzes' was requested, you MUST include a 'quiz' object for this module. Exactly {Config.MAX_QUIZ_QUESTIONS} questions.\n"
    if include_flashcards:
        SYSTEM_PROMPT += f"8. Since 'flashcards' was requested, you MUST include a 'flashcard_deck' object for this module. Exactly {Config.MAX_FLASHCARDS} cards.\n"

    SYSTEM_PROMPT += f"""
IMPORTANT: Output MUST be valid JSON matching this exact structure:
{expected_schema}
"""
    return expected_schema, SYSTEM_PROMPT


def _parse_module_json(
    data: dict,
    include_quizzes: bool,
    include_flashcards: bool,
    module_index: int,
) -> tuple[list[LessonContent], list[Quiz], list[FlashcardDeck]]:
    """Parse the JSON dict returned for a single module into Pydantic objects."""
    import re

    lessons: list[LessonContent] = []
    quizzes: list[Quiz] = []
    flashcards: list[FlashcardDeck] = []

    for l_data in data.get("lessons", []):
        segments = []
        # Enumerate from 1 so slide_index is always 1, 2, 3 … within each lesson.
        # This guarantees the filename written by the orchestrator matches what
        # the frontend requests and what slide_builder looks up — regardless of
        # whatever number Gemini happened to put in the JSON (Bug #3 fix).
        for seq_idx, s_data in enumerate(l_data.get("segments", []), start=1):
            raw_table = s_data.get("table_data")
            table_data = None
            if raw_table and isinstance(raw_table, dict):
                headers = raw_table.get("headers", [])
                rows = raw_table.get("rows", [])
                rows = [[str(cell)[:80] for cell in row] for row in rows]
                table_data = TableData(headers=headers, rows=rows)

            image_query = s_data.get("image_query")
            if image_query:
                image_query = re.sub(r'[^a-zA-Z0-9 ]', '', image_query).strip()
                image_query = ' '.join(image_query.split()[:4])

            segments.append(LessonSegment(
                slide_index=seq_idx,                          # always 1/2/3
                slide_title=s_data.get("slide_title", ""),
                slide_bullets=s_data.get("slide_bullets", []),
                narration=s_data.get("narration", ""),
                slide_type=s_data.get("slide_type", "text"),
                image_query=image_query,
                table_data=table_data
            ))


        raw_essay = l_data.get("lesson_essay", "")
        lesson_essay = raw_essay.strip() if isinstance(raw_essay, str) else ""

        lessons.append(LessonContent(
            module_index=l_data.get("module_index", module_index),
            lesson_index=l_data.get("lesson_index", 1),
            title=l_data.get("title", ""),
            segments=segments,
            key_takeaways=l_data.get("key_takeaways", []),
            lesson_essay=lesson_essay
        ))

    # Quiz — stored as single object "quiz" or inside "quizzes" list (handle both)
    if include_quizzes:
        quiz_data = data.get("quiz") or (data.get("quizzes", [None])[0] if data.get("quizzes") else None)
        if quiz_data and isinstance(quiz_data, dict):
            try:
                # Ensure module_index is correct even if model drifted
                quiz_data["module_index"] = module_index
                questions = [QuizQuestion(**q) for q in quiz_data.get("questions", [])]
                quizzes.append(Quiz(module_index=module_index, questions=questions))
            except Exception as e:
                print(f"[generate_full_content]   ⚠ Quiz parse error for module {module_index}: {e}")

    # Flashcard deck — stored as "flashcard_deck" or "flashcards" list
    if include_flashcards:
        deck_data = data.get("flashcard_deck") or (data.get("flashcards", [None])[0] if data.get("flashcards") else None)
        if deck_data and isinstance(deck_data, dict):
            try:
                deck_data["module_index"] = module_index
                cards = [Flashcard(**c) for c in deck_data.get("cards", [])]
                flashcards.append(FlashcardDeck(module_index=module_index, cards=cards))
            except Exception as e:
                print(f"[generate_full_content]   ⚠ Flashcard parse error for module {module_index}: {e}")

    return lessons, quizzes, flashcards


async def _generate_module_content(
    module: ModuleStub,
    params: dict,
    outline: CourseOutline,
    compressed_source: str,
    include_audio: bool,
    include_quizzes: bool,
    include_flashcards: bool,
) -> tuple[list[LessonContent], list[Quiz], list[FlashcardDeck]]:
    """
    Call Gemini once for a single module. Returns (lessons, quizzes, flashcards).
    Retries up to 3 times with continuation/correction on failure.
    """
    _, SYSTEM_PROMPT = _build_schema_and_system_prompt(
        include_audio, include_quizzes, include_flashcards
    )

    # ── Build per-module user prompt ──────────────────────────────────────────
    module_outline_json = json.dumps({
        "index": module.index,
        "title": module.title,
        "learning_objectives": module.learning_objectives,
        "lessons": [{"index": l.index, "title": l.title} for l in module.lessons]
    }, indent=2)

    base_prompt = ""

    if compressed_source and compressed_source.strip():
        base_prompt += f"""Source Knowledge Base (distilled from the uploaded document — use this to
ground your slide content, essays, and examples in the actual source material):
{compressed_source.strip()}

"""

    base_prompt += f"""Course Parameters:
- Title: {outline.title}
- Target Audience: {params.get('audience', 'General')}
- Level: {params.get('level')}
- Tone: {params.get('tone')}

Module to Generate (GENERATE ONLY THIS MODULE):
{module_outline_json}
"""

    client = get_genai_client()
    current_prompt = base_prompt
    malformed_text = ""
    error_msg = ""

    for attempt in range(3):
        print(f"\n[generate_full_content] Module {module.index} — Sending to Gemini (Attempt {attempt + 1})...")
        try:
            is_truncated = False
            mime_type = "application/json"

            if attempt > 0 and malformed_text:
                is_truncated = not (
                    malformed_text.strip().endswith("}") or malformed_text.strip().endswith("]")
                )
                if is_truncated:
                    print(f"[generate_full_content] Module {module.index} — Attempting CONTINUATION...")
                    correction_prompt = f"""You are continuing a JSON generation task for Module {module.index}.
Here was the original context and instructions:
---
{base_prompt}
---

ISSUE: TRUNCATION
Your previous JSON output was cut off midway because it exceeded the token limit.
Here is the exact partial text you generated before being cut off:
---
{malformed_text}
---

TASK: CONTINUATION
Please output ONLY the remaining text required to complete the JSON. Do NOT start from the beginning.
Start EXACTLY where the text cut off, continuing the syntax so that if I append your new output to the partial text, it forms a perfectly valid JSON object matching the requested schema.
Do NOT wrap your output in markdown ```json or backticks. Just output the raw text continuation."""
                    current_prompt = correction_prompt
                    mime_type = "text/plain"
                else:
                    print(f"[generate_full_content] Module {module.index} — Attempting SYNTAX CORRECTION...")
                    correction_prompt = f"""You are correcting a JSON generation task for Module {module.index}.
Here was the original context and instructions:
---
{base_prompt}
---

ISSUE: SYNTAX ERROR
Your previous JSON output failed to parse with this error: {error_msg}

Here is the malformed JSON text:
---
{malformed_text}
---

TASK: CORRECTION
Please fix the syntax errors (e.g. missing commas, unescaped quotes) and output the COMPLETE, valid JSON.
Output ONLY the raw valid JSON matching the requested schema."""
                    current_prompt = correction_prompt
                    mime_type = "application/json"

            response = await client.aio.models.generate_content_stream(
                model=Config.MODEL_NAME,
                contents=current_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.32 if attempt == 0 else 0.1,
                    response_mime_type=mime_type,
                    max_output_tokens=32768
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
            print(f"\n[generate_full_content] Module {module.index} — Finished receiving response.")

            if not text or not text.strip():
                raise Exception(f"Generative API returned empty response for module {module.index}.")

            if attempt > 0 and is_truncated:
                continuation = text.strip()
                if continuation.startswith("```json"):
                    continuation = continuation[7:]
                if continuation.startswith("```"):
                    continuation = continuation[3:]
                if continuation.endswith("```"):
                    continuation = continuation[:-3]
                full_text = malformed_text + continuation
            else:
                full_text = text

            cleaned = clean_json_string(full_text)

            try:
                data = json.loads(cleaned)
            except json.JSONDecodeError as jde:
                malformed_text = full_text
                error_msg = str(jde)
                raise jde

            return _parse_module_json(data, include_quizzes, include_flashcards, module.index)

        except Exception as e:
            print(f"[generate_full_content] Module {module.index} — Attempt {attempt + 1} failed: {e}")
            if attempt == 2:
                raise Exception(
                    f"Failed to generate content for module {module.index} after 3 attempts. Last error: {e}"
                )
            await asyncio.sleep(1)

    # Should never reach here
    return [], [], []


async def generate_full_content(
    params: dict, outline: CourseOutline, compressed_source: str = ""
) -> FullCourseContent:
    """
    Generate content for ALL modules by calling Gemini once per module, in parallel.

    Running modules concurrently with asyncio.gather() means the total wall-clock
    time is roughly equal to generating ONE module — not N modules sequentially.
    Total token cost is nearly identical to a single monolithic call (the only
    overhead is the system prompt being included once per module in the input,
    which is negligible since input tokens are ~5x cheaper than output tokens).

    This also eliminates the token-limit truncation that occurred when generating
    5 modules in a single API call, which silently dropped modules 2-5 from the
    lessons array.
    """
    content_types = params.get('content_types', [])
    include_audio = 'video' in content_types or 'audio' in content_types
    include_quizzes = 'quizzes' in content_types
    include_flashcards = 'flashcards' in content_types

    print(f"\n[generate_full_content] Launching {len(outline.modules)} module call(s) in parallel...")

    async def _safe_generate(module):
        """Wraps _generate_module_content so gather() collects results not exceptions."""
        try:
            print(f"[generate_full_content] ↦ Starting Module {module.index}: {module.title}")
            result = await _generate_module_content(
                module=module,
                params=params,
                outline=outline,
                compressed_source=compressed_source,
                include_audio=include_audio,
                include_quizzes=include_quizzes,
                include_flashcards=include_flashcards,
            )
            lessons, quizzes, flashcards = result
            print(f"[generate_full_content] ✓ Module {module.index} done: "
                  f"{len(lessons)} lesson(s), {len(quizzes)} quiz(zes), {len(flashcards)} deck(s).")
            return module.index, result
        except Exception as e:
            print(f"[generate_full_content] ✗ Module {module.index} FAILED after retries: {e}")
            return module.index, ([], [], [])   # empty but non-crashing

    # Fire all module calls simultaneously — Vertex AI enterprise handles this easily
    raw_results = await asyncio.gather(*[_safe_generate(m) for m in outline.modules])

    # Re-assemble in original module order so lesson_index lookups stay consistent
    full_content = FullCourseContent(lessons=[], quizzes=[], flashcards=[])
    for _module_idx, (lessons, quizzes, flashcards) in sorted(raw_results, key=lambda r: r[0]):
        full_content.lessons.extend(lessons)
        full_content.quizzes.extend(quizzes)
        full_content.flashcards.extend(flashcards)

    total_lessons = len(full_content.lessons)
    total_expected = sum(len(m.lessons) for m in outline.modules)
    print(f"\n[generate_full_content] ═══ All modules complete: "
          f"{total_lessons}/{total_expected} lessons, "
          f"{len(full_content.quizzes)} quizzes, "
          f"{len(full_content.flashcards)} flashcard decks ═══")

    if total_lessons == 0:
        raise Exception("Content generation produced zero lessons. All module calls failed.")

    return full_content
