from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import uuid
from sse_starlette.sse import EventSourceResponse
import json
import os
import time

from pipeline.orchestrator import run_pipeline
from config import Config

router = APIRouter()

class GenerateRequest(BaseModel):
    prompt: str
    audience: Optional[str] = ""
    voice: Optional[str] = "en-US-JennyNeural"
    blueprint: str
    duration: str
    level: str
    tone: str
    content_types: List[str]
    file_id: Optional[str] = None

# In-memory job store for MVP. Format: job_id -> {"req": req, "timestamp": float}
jobs = {}

@router.post("/generate")
async def start_generation(req: GenerateRequest):
    # m12: Validate input fields
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")
    if not req.content_types:
        raise HTTPException(status_code=400, detail="At least one content type must be selected.")
        
    valid_types = {'text', 'quizzes', 'flashcards', 'video', 'audio'}
    invalid_types = set(req.content_types) - valid_types
    if invalid_types:
        raise HTTPException(status_code=400, detail=f"Invalid content type(s): {', '.join(invalid_types)}")

    # Prune jobs older than 1 hour to prevent memory leaks if stream never starts
    now = time.time()
    expired_jobs = [jid for jid, job_data in jobs.items() if now - job_data.get("timestamp", 0) > 3600]
    for jid in expired_jobs:
        jobs.pop(jid, None)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "req": req,
        "timestamp": now
    }
    return {"job_id": job_id}

@router.get("/generate/stream/{job_id}")
async def stream_generation(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job_data = jobs[job_id]
    req = job_data["req"]
    
    source_text = ""
    if req.file_id:
        text_path = os.path.join(Config.DOCS_DIR, f"{req.file_id}.txt")
        if os.path.exists(text_path):
            with open(text_path, "r", encoding="utf-8") as f:
                source_text = f.read()

    # Issue 3 fix: hard cap at 6,000 words to prevent context overflow.
    # A 30-page document is ~15,000 words; 6,000 words covers ~18 dense pages
    # while leaving ample room for the outline + compressed_source output.
    MAX_SOURCE_WORDS = 6000
    words = source_text.split()
    if len(words) > MAX_SOURCE_WORDS:
        source_text = " ".join(words[:MAX_SOURCE_WORDS])
        print(f"[generate] ⚠ Source text truncated: {len(words)} → {MAX_SOURCE_WORDS} words.")

    async def event_generator():
        try:
            async for event in run_pipeline(req.model_dump(), source_text, job_id):
                yield {"data": json.dumps(event)}
        finally:
            jobs.pop(job_id, None)
            
    return EventSourceResponse(event_generator())

@router.get("/course/{course_id}")
async def get_course(course_id: str):
    # Try fetching from DB first, fallback to file if needed (we'll just use the file for now as it's perfectly in sync)
    path = os.path.join(Config.COURSE_OUTPUT_DIR, f"{course_id}.json")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/json")
    # m9: Raise proper 404 response
    raise HTTPException(status_code=404, detail="Course not found")

@router.get("/courses")
async def list_courses():
    from database import SessionLocal
    from models.orm import CourseModel
    db = SessionLocal()
    try:
        courses = db.query(CourseModel).order_by(CourseModel.created_at.desc()).all()
        return [{"id": c.id, "title": c.title, "description": c.description, "created_at": c.created_at} for c in courses]
    finally:
        db.close()
