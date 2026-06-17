from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
from config import Config
from document.processor import extract_text

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # M6: Enforce 20MB file size limit
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds the 20MB limit.")
        
    file_id = str(uuid.uuid4())
    os.makedirs(Config.DOCS_DIR, exist_ok=True)
    
    # Read file content in chunks to avoid overloading memory (M6)
    file_bytes = b""
    chunk_size = 1024 * 1024  # 1MB
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_bytes += chunk
        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds the 20MB limit.")
            
    source_text = extract_text(file_bytes, file.filename)
    
    text_path = os.path.join(Config.DOCS_DIR, f"{file_id}.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(source_text)
        
    return {"file_id": file_id, "filename": file.filename, "text_length": len(source_text)}

@router.delete("/uploads/{file_id}")
async def delete_document(file_id: str):
    # M7: Missing DELETE endpoint implementation
    text_path = os.path.join(Config.DOCS_DIR, f"{file_id}.txt")
    if os.path.exists(text_path):
        try:
            os.remove(text_path)
            return {"status": "success", "message": "File deleted successfully"}
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file from disk: {str(e)}")
    raise HTTPException(status_code=404, detail="File not found")
