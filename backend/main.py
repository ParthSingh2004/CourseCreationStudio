from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Limit the integer string conversion limit (fixes error with huge numbers in LLM JSON, avoids DoS)
sys.set_int_max_str_digits(50000)

from api import upload, generate, export, enhance
from config import Config
from database import engine, Base
import models.orm

# Create database tables
Base.metadata.create_all(bind=engine)

# SQLite database migration check for updated_at column (m10)
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE courses ADD COLUMN updated_at DATETIME"))
        conn.commit()
    except Exception:
        pass

app = FastAPI(title="Chapter AI Course Generator")

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
env_origins = os.getenv("ALLOWED_ORIGINS")
if env_origins:
    allowed_origins.extend([o.strip() for o in env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/v1")
app.include_router(generate.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1/export")
app.include_router(enhance.router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}
