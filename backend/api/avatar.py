import os
import asyncio
import base64
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

class NarrateRequest(BaseModel):
    text: str
    presenter: str = "amy"
    course_id: str = ""
    module_idx: int = 1
    lesson_idx: int = 1

DEFAULT_PRESENTERS = {
    "amy": "https://clips-presenters.d-id.com/amy/image.png",
    "matt": "https://clips-presenters.d-id.com/matt/image.png",
}

# Global in-memory cache for avatar job status
# Format: lesson_key ("{course_id}_{module_idx}_{lesson_idx}") -> {"status": "rendering"|"ready"|"failed", "video_url": str, "error": str}
AVATAR_JOBS: Dict[str, Dict[str, Any]] = {}

def get_d_id_auth_header() -> dict:
    api_key = os.getenv("D_ID_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="D_ID_API_KEY environment variable is not set. Please set your D-ID API key in Render settings."
        )
    
    if api_key.startswith("Basic "):
        auth_str = api_key
    elif ":" in api_key:
        b64_key = base64.b64encode(api_key.encode("utf-8")).decode("utf-8")
        auth_str = f"Basic {b64_key}"
    else:
        auth_str = f"Basic {api_key}"

    return {
        "Authorization": auth_str,
        "Content-Type": "application/json",
        "accept": "application/json"
    }

async def generate_avatar_task(lesson_key: str, text_content: str, presenter: str = "amy"):
    """Background worker task to generate D-ID avatar without blocking API gateways."""
    AVATAR_JOBS[lesson_key] = {"status": "rendering", "video_url": "", "error": ""}
    
    try:
        api_key = os.getenv("D_ID_API_KEY", "").strip()
        if not api_key:
            AVATAR_JOBS[lesson_key] = {"status": "failed", "error": "D_ID_API_KEY is not set."}
            return

        if ":" in api_key:
            b64_key = base64.b64encode(api_key.encode("utf-8")).decode("utf-8")
            auth_str = f"Basic {b64_key}"
        elif api_key.startswith("Basic "):
            auth_str = api_key
        else:
            auth_str = f"Basic {api_key}"

        headers = {
            "Authorization": auth_str,
            "Content-Type": "application/json",
            "accept": "application/json"
        }

        # Truncate long text for speed & credit safety
        clean_text = text_content.strip()
        if len(clean_text) > 450:
            clean_text = clean_text[:447] + "..."

        source_url = DEFAULT_PRESENTERS.get(presenter.lower(), DEFAULT_PRESENTERS["amy"])

        payload = {
            "script": {
                "type": "text",
                "subtitles": "false",
                "provider": {
                    "type": "microsoft",
                    "voice_id": "en-US-JennyNeural" if presenter.lower() == "amy" else "en-US-GuyNeural"
                },
                "input": clean_text
            },
            "config": {
                "fluent": "false",
                "pad_audio": "0.0"
            },
            "source_url": source_url
        }

        print(f"[avatar_bg] Posting D-ID talk job for lesson {lesson_key}...")
        resp = await asyncio.to_thread(
            requests.post,
            "https://api.d-id.com/talks",
            json=payload,
            headers=headers,
            timeout=15
        )

        if resp.status_code not in (200, 201):
            err_msg = f"D-ID API returned {resp.status_code}: {resp.text}"
            print(f"[avatar_bg] ✗ {err_msg}")
            AVATAR_JOBS[lesson_key] = {"status": "failed", "error": err_msg}
            return

        data = resp.json()
        talk_id = data.get("id")
        if not talk_id:
            AVATAR_JOBS[lesson_key] = {"status": "failed", "error": "No talk_id returned by D-ID"}
            return

        # Poll D-ID for up to 90 seconds in the background
        poll_url = f"https://api.d-id.com/talks/{talk_id}"
        for _ in range(45):
            await asyncio.sleep(2)
            try:
                poll_resp = await asyncio.to_thread(
                    requests.get,
                    poll_url,
                    headers=headers,
                    timeout=10
                )
                if poll_resp.status_code == 200:
                    status_data = poll_resp.json()
                    st = status_data.get("status")
                    if st == "done":
                        video_url = status_data.get("result_url")
                        if video_url:
                            print(f"[avatar_bg] ✓ Avatar ready for {lesson_key}: {video_url[:60]}...")
                            AVATAR_JOBS[lesson_key] = {"status": "ready", "video_url": video_url, "talk_id": talk_id}
                            return
                    elif st == "error":
                        err_detail = str(status_data.get("error", "D-ID render error"))
                        print(f"[avatar_bg] ✗ D-ID render error for {lesson_key}: {err_detail}")
                        AVATAR_JOBS[lesson_key] = {"status": "failed", "error": err_detail}
                        return
            except Exception as poll_e:
                print(f"[avatar_bg] Warning during polling {lesson_key}: {poll_e}")

        AVATAR_JOBS[lesson_key] = {"status": "failed", "error": "D-ID generation timed out after 90s"}

    except Exception as exc:
        print(f"[avatar_bg] ✗ Unexpected error generating avatar for {lesson_key}: {exc}")
        AVATAR_JOBS[lesson_key] = {"status": "failed", "error": str(exc)}

def trigger_course_avatar_generation(course, presenter: str = "amy"):
    """
    Non-blocking helper called by orchestrator during course writing step.
    Kicks off background avatar rendering tasks for each lesson.
    """
    if not course.content or not course.content.lessons:
        return

    for lesson in course.content.lessons:
        lesson_key = f"{course.course_id}_{lesson.module_index}_{lesson.lesson_index}"
        
        # Collect narration text from segments
        narration_parts = [s.narration for s in lesson.segments if s.narration and s.narration.strip()]
        text_to_narrate = " ".join(narration_parts) if narration_parts else lesson.title
        
        # Mark as rendering and spawn async background task
        AVATAR_JOBS[lesson_key] = {"status": "rendering", "video_url": "", "error": ""}
        asyncio.create_task(generate_avatar_task(lesson_key, text_to_narrate, presenter))


@router.get("/avatar/status/{course_id}/{module_idx}/{lesson_idx}")
async def get_avatar_status(course_id: str, module_idx: int, lesson_idx: int):
    """
    Get background rendering status for a specific lesson avatar.
    Returns {"status": "rendering"|"ready"|"failed", "video_url": "..."}
    """
    lesson_key = f"{course_id}_{module_idx}_{lesson_idx}"
    job_info = AVATAR_JOBS.get(lesson_key)
    
    if not job_info:
        api_key = os.getenv("D_ID_API_KEY", "").strip()
        if not api_key:
            return {"status": "failed", "error": "D_ID_API_KEY is not configured in Render environment.", "video_url": ""}
            
        try:
            from api.export import _load_course
            course = _load_course(course_id)
            if course and course.content and course.content.lessons:
                lesson = next((l for l in course.content.lessons if l.module_index == module_idx and l.lesson_index == lesson_idx), None)
                if lesson:
                    narration_parts = [s.narration for s in lesson.segments if s.narration and s.narration.strip()]
                    text_to_narrate = " ".join(narration_parts) if narration_parts else lesson.title
                    AVATAR_JOBS[lesson_key] = {"status": "rendering", "video_url": "", "error": ""}
                    asyncio.create_task(generate_avatar_task(lesson_key, text_to_narrate, "amy"))
                    return {"status": "rendering", "video_url": "", "error": ""}
        except Exception as e:
            print(f"[avatar_status] Auto-start info: {e}")
            
        return {"status": "failed", "error": "Avatar task not found.", "video_url": ""}
        
    return job_info


@router.post("/avatar/narrate")
async def generate_avatar_narration(req: NarrateRequest):
    """
    On-demand endpoint: if already rendering or ready, return status immediately.
    Otherwise, kick off background task and return rendering status (no HTTP 504 timeouts).
    """
    lesson_key = f"{req.course_id}_{req.module_idx}_{req.lesson_idx}" if req.course_id else "temp_lesson"
    
    existing = AVATAR_JOBS.get(lesson_key)
    if existing and existing.get("status") == "ready":
        return {"status": "success", "video_url": existing.get("video_url"), "talk_id": existing.get("talk_id")}
        
    if existing and existing.get("status") == "rendering":
        return {"status": "rendering", "message": "Avatar is rendering in background"}

    # Start background task if not already running
    asyncio.create_task(generate_avatar_task(lesson_key, req.text, req.presenter))
    return {"status": "rendering", "message": "Avatar rendering started in background"}
