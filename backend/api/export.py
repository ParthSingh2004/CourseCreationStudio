from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
import os
from config import Config
from exporters.image_fetcher import fetch_unsplash_image

router = APIRouter()


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
            detail="Could not fetch an image for that query. Check UNSPLASH_ACCESS_KEY in .env."
        )

    return Response(content=img_bytes, media_type="image/jpeg")


@router.get("/image/{job_id}/{module_idx}/{lesson_idx}/{slide_idx}")
async def serve_static_image(job_id: str, module_idx: int, lesson_idx: int, slide_idx: int):
    filename = f"{job_id}_{module_idx}_{lesson_idx}_{slide_idx}.jpg"
    path = os.path.join(Config.IMAGE_OUTPUT_DIR, filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="image/jpeg")
    raise HTTPException(status_code=404, detail="Image not found")

@router.get("/{course_id}/slides")
async def export_slides(course_id: str):
    path = os.path.join(Config.SLIDES_OUTPUT_DIR, f"{course_id}.pptx")
    if os.path.exists(path):
        return FileResponse(path, filename="Course_Slides.pptx")
    raise HTTPException(status_code=404, detail="Slides export not found")

@router.get("/{course_id}/quiz-pdf")
async def export_quiz_pdf(course_id: str):
    path = os.path.join(Config.PDF_OUTPUT_DIR, f"{course_id}_quiz.pdf")
    if os.path.exists(path):
        return FileResponse(path, filename="Course_Quiz.pdf")
    raise HTTPException(status_code=404, detail="Quiz PDF export not found")

@router.get("/{course_id}/summary-pdf")
async def export_summary_pdf(course_id: str):
    path = os.path.join(Config.PDF_OUTPUT_DIR, f"{course_id}_summary.pdf")
    if os.path.exists(path):
        return FileResponse(path, filename="Course_Summary.pdf")
    raise HTTPException(status_code=404, detail="Summary PDF export not found")

@router.get("/audio/{lesson_id}")
async def export_audio(lesson_id: str):
    path = os.path.join(Config.AUDIO_OUTPUT_DIR, f"{lesson_id}_full.mp3")
    if os.path.exists(path):
        return FileResponse(path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Audio file not found")
