from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import Config
import os

# Ensure the database directory exists
os.makedirs(Config.DATA_ROOT, exist_ok=True)
os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.COURSE_OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.SLIDES_OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.PDF_OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.AUDIO_OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.IMAGE_OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.DOCS_DIR, exist_ok=True)

connect_args = {}
pool_recycle = -1
if Config.DB_PATH.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Serverless databases (Neon/Supabase) close idle connections after a few minutes.
    # Recycle connections every 280 seconds and use pool_pre_ping to check connection health.
    pool_recycle = 280

engine = create_engine(
    Config.DB_PATH,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=pool_recycle
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
