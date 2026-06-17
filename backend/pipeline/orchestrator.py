import asyncio
from typing import AsyncGenerator
import os
import json
from config import Config
from database import SessionLocal
from models.orm import CourseModel
from models.schemas import GeneratedCourse, CourseOutline
from pipeline.steps.call_1_design import generate_course_design
from pipeline.steps.call_2_full_content import generate_full_content
from tts.audio_builder import generate_course_audio
from exporters.slide_builder import build_slides
from exporters.pdf_builder import build_quiz_pdf, build_summary_pdf
from exporters.image_fetcher import fetch_unsplash_image

# STEPS are now dynamically built in run_pipeline

async def run_pipeline(params: dict, source_text: str, job_id: str) -> AsyncGenerator:
    course = GeneratedCourse(
        course_id=job_id,
        outline=CourseOutline(title="", description="", total_modules=0, modules=[])
    )
    
    content_types = params.get('content_types', [])
    
    # Dynamically construct STEPS based on requested content types
    STEPS = [("design", "Designing your curriculum...")]
    
    if any(ct in content_types for ct in ['text', 'quizzes', 'flashcards', 'video', 'audio']):
        STEPS.append(("write", "Writing content..."))
        
    if 'video' in content_types or 'audio' in content_types:
        STEPS.append(("audio", "Synthesizing Audio & Script..."))

    # Slides always run when content is written — not just for video
    if any(ct in content_types for ct in ['text', 'quizzes', 'flashcards', 'video', 'audio']):
        STEPS.append(("slides", "Building slide deck..."))
        
    if 'quizzes' in content_types or 'text' in content_types:
        STEPS.append(("pdf", "Exporting PDFs..."))

    # Yield list of active steps for the frontend to render dynamically (M1)
    yield {"step": "init", "steps": [sid for sid, _ in STEPS]}

    has_error = False
    compressed_source = ""   # populated by "design" step, consumed by "write" step

    for step_id, label in STEPS:
        yield {"step": step_id, "label": label, "status": "running"}
        
        try:
            if step_id == "design":
                outline, compressed_source = await generate_course_design(params, source_text)
                course.outline = outline
                if compressed_source:
                    print(f"[orchestrator] ✓ compressed_source captured "
                          f"({len(compressed_source.split())} words) — will pass to Call 2.")
                
            elif step_id == "write":
                if not course.outline or not course.outline.title:
                    raise Exception("Outline is missing. Cannot write content.")
                content = await generate_full_content(params, course.outline, compressed_source)
                course.content = content
                
                if course.content and course.content.lessons:
                    # Ensure the output directory exists before any writes (Bug #2 fix)
                    os.makedirs(Config.IMAGE_OUTPUT_DIR, exist_ok=True)

                    for lesson in course.content.lessons:
                        for segment in lesson.segments:
                            if segment.slide_type == "photo" and segment.image_query:
                                print(f"[orchestrator] Fetching static image for query: {segment.image_query}")
                                img_bytes = await asyncio.to_thread(fetch_unsplash_image, segment.image_query)
                                if img_bytes:
                                    img_path = os.path.join(
                                        Config.IMAGE_OUTPUT_DIR,
                                        f"{job_id}_{lesson.module_index}_{lesson.lesson_index}_{segment.slide_index}.jpg"
                                    )
                                    try:
                                        with open(img_path, "wb") as f:
                                            f.write(img_bytes)
                                        print(f"[orchestrator]   ✓ Saved image → {img_path}")
                                    except Exception as img_err:
                                        print(f"[orchestrator]   ✗ Failed to save image to {img_path}: {img_err}")
                
            elif step_id == "audio":
                if course.content and course.content.lessons:
                    voice = params.get('voice', 'en-US-JennyNeural')
                    audio_data = await generate_course_audio(course.content.lessons, job_id, voice)
                    course.audio = audio_data
                
            elif step_id == "slides":
                slide_path = await asyncio.to_thread(build_slides, course)
                course.slide_path = slide_path
                
            elif step_id == "pdf":
                quiz_pdf = await asyncio.to_thread(build_quiz_pdf, course)
                summary_pdf = await asyncio.to_thread(build_summary_pdf, course)
                course.quiz_pdf_path = quiz_pdf
                course.summary_pdf_path = summary_pdf
                
            yield {"step": step_id, "label": label, "status": "done"}
        except Exception as e:
            yield {"step": step_id, "label": label, "status": "error", "error": str(e)}
            has_error = True
            break

    if not has_error:
        # Save course JSON for viewer to fetch
        await asyncio.to_thread(save_course, course)
        yield {"step": "complete", "course_id": job_id}

def save_course(course: GeneratedCourse):
    # Save to JSON file as backup/compatibility
    path = os.path.join(Config.COURSE_OUTPUT_DIR, f"{course.course_id}.json")
    with open(path, "w") as f:
        f.write(course.model_dump_json(indent=2))
        
    # Save to Database
    db = SessionLocal()
    try:
        db_course = CourseModel(
            id=course.course_id,
            title=course.outline.title if course.outline else "Untitled",
            description=course.outline.description if course.outline else "",
            json_content=course.model_dump_json(indent=2)
        )
        db.merge(db_course)
        db.commit()
    finally:
        db.close()
