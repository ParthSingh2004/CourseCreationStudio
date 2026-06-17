from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from config import Config, get_genai_client
from google.genai import types

router = APIRouter()


class EnhanceRequest(BaseModel):
    prompt: str

class EnhanceResponse(BaseModel):
    enhanced_prompt: str

SYSTEM_INSTRUCTION = (
    "You are an expert curriculum designer. The user will give you a short idea for a course. "
    "Your job is to expand it into a dense, structural blueprint (2-3 paragraphs) that will be used "
    "to generate the actual course content. Do NOT write a marketing pitch or use phrases like "
    "'This course is designed for...'. Instead, write directly about what the course MUST cover. "
    "Clearly outline the target audience, the core learning objectives, and detail the specific modules "
    "and topics that must be generated. Return ONLY the expanded blueprint, in clear paragraphs without "
    "markdown headers."
)

@router.post("/enhance-prompt", response_model=EnhanceResponse)
async def enhance_prompt(req: EnhanceRequest):
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
        
    client = get_genai_client()
    
    try:
        response = await client.aio.models.generate_content(
            model=Config.MODEL_NAME,
            contents=req.prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        
        try:
            text = response.text
        except ValueError as ve:
            # Handles M11 safety filter blocks gracefully
            raise HTTPException(status_code=400, detail="Prompt was flagged or blocked by safety filters.")
            
        if not text or not text.strip():
            raise HTTPException(status_code=500, detail="Model returned an empty response.")
            
        return EnhanceResponse(enhanced_prompt=text.strip())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enhance prompt: {str(e)}")
