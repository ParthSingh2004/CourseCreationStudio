import os
import asyncio
import base64
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import Config

router = APIRouter()

class NarrateRequest(BaseModel):
    text: str
    presenter: str = "amy"  # "amy" or "matt"

DEFAULT_PRESENTERS = {
    "amy": "https://create-images-results.d-id.com/DefaultPresenters/Amy_f/v2_image.jpeg",
    "matt": "https://create-images-results.d-id.com/DefaultPresenters/Matt_m/v2_image.jpeg",
}

def get_d_id_auth_header() -> dict:
    api_key = os.getenv("D_ID_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="D_ID_API_KEY environment variable is not set. Please set your D-ID API key in Render settings."
        )
    
    # Handle plain key vs base64 vs username:password format
    if api_key.startswith("Basic "):
        auth_str = api_key
    elif ":" in api_key:
        b64_key = base64.b64encode(api_key.encode("utf-8")).decode("utf-8")
        auth_str = f"Basic {b64_key}"
    else:
        # Key is already base64 token or single API key string
        auth_str = f"Basic {api_key}"

    return {
        "Authorization": auth_str,
        "Content-Type": "application/json",
        "accept": "application/json"
    }

@router.post("/avatar/narrate")
async def generate_avatar_narration(req: NarrateRequest):
    """
    1-Shot POC Endpoint for D-ID Avatar Lesson Narration.
    Generates a talking head video MP4 for the provided text using D-ID API.
    """
    text_content = req.text.strip()
    if not text_content:
        raise HTTPException(status_code=400, detail="Narration text is required.")

    # Limit text length for quick POC generation speed (< 400 chars per request)
    if len(text_content) > 500:
        text_content = text_content[:497] + "..."

    headers = get_d_id_auth_header()
    source_url = DEFAULT_PRESENTERS.get(req.presenter.lower(), DEFAULT_PRESENTERS["amy"])

    # 1. Create Talk Job
    payload = {
        "script": {
            "type": "text",
            "subtitles": "true",
            "provider": {
                "type": "microsoft",
                "voice_id": "en-US-JennyNeural" if req.presenter.lower() == "amy" else "en-US-GuyNeural"
            },
            "input": text_content
        },
        "config": {
            "fluent": "false",
            "pad_audio": "0.0"
        },
        "source_url": source_url
    }

    try:
        resp = await asyncio.to_thread(
            requests.post,
            "https://api.d-id.com/talks",
            json=payload,
            headers=headers,
            timeout=15
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to D-ID API: {e}")

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"D-ID API error ({resp.status_code}): {resp.text}"
        )

    data = resp.json()
    talk_id = data.get("id")
    if not talk_id:
        raise HTTPException(status_code=500, detail="D-ID did not return a valid talk_id.")

    # 2. Poll Talk Job Status (max 30 seconds)
    poll_url = f"https://api.d-id.com/talks/{talk_id}"
    for _ in range(15):
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
                status = status_data.get("status")
                if status == "done":
                    video_url = status_data.get("result_url")
                    if video_url:
                        return {"status": "success", "video_url": video_url, "talk_id": talk_id}
                elif status == "error":
                    raise HTTPException(
                        status_code=500,
                        detail=f"D-ID generation failed: {status_data.get('error', {})}"
                    )
        except HTTPException:
            raise
        except Exception as poll_err:
            print(f"[avatar] Polling warning: {poll_err}")

    raise HTTPException(status_code=504, detail="D-ID video generation timed out. Please try again.")
