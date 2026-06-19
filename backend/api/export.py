import asyncio
import json
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from config import Config
from exporters.image_fetcher import fetch_unsplash_image
from exporters.pdf_builder import build_quiz_pdf, build_summary_pdf
from exporters.slide_builder import build_slides
from models.schemas import GeneratedCourse

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_course(course_id: str) -> GeneratedCourse:
    """Load a GeneratedCourse from the database (fallback to JSON file), or raise 404."""
    # Try fetching from DB first
    from database import SessionLocal
    from models.orm import CourseModel
    db = SessionLocal()
    try:
        db_course = db.query(CourseModel).filter(CourseModel.id == course_id).first()
        if db_course and db_course.json_content:
            return GeneratedCourse.model_validate_json(db_course.json_content)
    except Exception as e:
        print(f"Error loading course {course_id} from DB: {e}")
    finally:
        db.close()

    # Fallback to local JSON file
    path = os.path.join(Config.COURSE_OUTPUT_DIR, f"{course_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Course not found")
    with open(path, "r", encoding="utf-8") as f:
        return GeneratedCourse.model_validate_json(f.read())



# ── image proxy (unchanged) ───────────────────────────────────────────────────

@router.get("/image")
async def proxy_image(q: str = Query(..., description="Search query for Unsplash")):
    """
    Proxy endpoint: fetches a topic-relevant image from Unsplash and returns
    the raw bytes. Keeps the API key server-side and avoids CORS issues.
    GET /api/v1/export/image?q=machine+learning+neural+network
    """
    if not q or not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required.")

    img_bytes = fetch_unsplash_image(q.strip())
    if img_bytes is None:
        raise HTTPException(
            status_code=404,
            detail="Could not fetch an image for that query. Check UNSPLASH_ACCESS_KEY in .env.",
        )

    return Response(content=img_bytes, media_type="image/jpeg")


@router.get("/image/{job_id}/{module_idx}/{lesson_idx}/{slide_idx}")
async def serve_static_image(job_id: str, module_idx: int, lesson_idx: int, slide_idx: int):
    filename = f"{job_id}_{module_idx}_{lesson_idx}_{slide_idx}.jpg"
    path = os.path.join(Config.IMAGE_OUTPUT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Image not found")


# ── on-demand document generation ────────────────────────────────────────────

@router.get("/{course_id}/slides")
async def export_slides(course_id: str):
    """
    Generate (or serve cached) a .pptx slide deck for the given course.
    The file is built on first request and cached on disk for subsequent calls.
    """
    output_path = os.path.join(Config.SLIDES_OUTPUT_DIR, f"{course_id}.pptx")

    if not os.path.exists(output_path):
        course = _load_course(course_id)
        await asyncio.to_thread(build_slides, course)

    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Slide generation failed — output file not found.")

    return FileResponse(
        output_path,
        filename="Course_Slides.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="Course_Slides.pptx"'},
    )


@router.get("/{course_id}/quiz-pdf")
async def export_quiz_pdf(course_id: str):
    """
    Generate (or serve cached) a Quiz PDF for the given course.
    The file is built on first request and cached on disk for subsequent calls.
    """
    output_path = os.path.join(Config.PDF_OUTPUT_DIR, f"{course_id}_quiz.pdf")

    if not os.path.exists(output_path):
        course = _load_course(course_id)
        result = await asyncio.to_thread(build_quiz_pdf, course)
        if result is None:
            raise HTTPException(status_code=422, detail="This course has no quiz content to export.")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Quiz PDF generation failed — output file not found.")

    return FileResponse(
        output_path,
        filename="Course_Quiz.pdf",
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Course_Quiz.pdf"'},
    )


@router.get("/{course_id}/summary-pdf")
async def export_summary_pdf(course_id: str):
    """
    Generate (or serve cached) a Summary PDF for the given course.
    The file is built on first request and cached on disk for subsequent calls.
    """
    output_path = os.path.join(Config.PDF_OUTPUT_DIR, f"{course_id}_summary.pdf")

    if not os.path.exists(output_path):
        course = _load_course(course_id)
        result = await asyncio.to_thread(build_summary_pdf, course)
        if result is None:
            raise HTTPException(status_code=422, detail="This course has no lesson content to export.")

    if not os.path.exists(output_path):
        raise HTTPException(status_code=500, detail="Summary PDF generation failed — output file not found.")

    return FileResponse(
        output_path,
        filename="Course_Summary.pdf",
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="Course_Summary.pdf"'},
    )


# ── audio (unchanged) ─────────────────────────────────────────────────────────

@router.get("/audio/{lesson_id}")
async def export_audio(lesson_id: str):
    path = os.path.join(Config.AUDIO_OUTPUT_DIR, f"{lesson_id}_full.mp3")
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Audio file not found")

