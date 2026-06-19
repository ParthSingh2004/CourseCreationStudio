import os
from dotenv import load_dotenv

load_dotenv()

from google import genai

class Config:
    # Model config
    VERTEX_AI_ENABLED = os.getenv("VERTEX_AI_ENABLED", "false").lower() == "true" or os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1") or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "").strip()
    if not VERTEX_AI_ENABLED and not GEMINI_API_KEY:
        raise ValueError(
            "Neither VERTEX_AI_ENABLED is true nor GEMINI_API_KEY environment variable is set. "
            "Please provide a valid GEMINI_API_KEY or enable Vertex AI in your .env file."
        )
    MODEL_NAME = "gemini-3.5-flash"  # As requested by user (fallback to gemini-1.5-flash or similar on Vertex if needed)

    # Generation limits
    MAX_MODULES = 5
    MAX_LESSONS_PER_MODULE = 3
    MAX_QUIZ_QUESTIONS = 5
    MAX_FLASHCARDS = 10
    MAX_SLIDES_PER_LESSON = 3

    # Storage paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Configurable data root, defaults to D:\CourseEngineData if D: exists on Windows, otherwise ~/CourseEngineData (m1)
    _default_data_root = r"D:\CourseEngineData"
    if os.name != "nt" or not os.path.exists("D:\\"):
        _default_data_root = os.path.expanduser("~/CourseEngineData")
    DATA_ROOT = os.getenv("COURSE_ENGINE_DATA_ROOT", _default_data_root)
    
    # Database
    _db_url = os.getenv("DATABASE_URL")
    if _db_url:
        # SQLAlchemy requires postgresql:// instead of postgres://
        if _db_url.startswith("postgres://"):
            _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        DB_PATH = _db_url
    else:
        DB_PATH = f"sqlite:///{os.path.join(DATA_ROOT, 'course_engine.db')}"
    
    # Media paths
    OUTPUT_DIR = os.path.join(DATA_ROOT, "media")
    COURSE_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "courses") # Still needed for backwards compatibility or exports if any
    SLIDES_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "slides")
    PDF_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "pdfs")
    AUDIO_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "audio")
    IMAGE_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "images")
    DOCS_DIR = os.path.join(DATA_ROOT, "uploads")

_genai_client = None

def get_genai_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        if Config.VERTEX_AI_ENABLED:
            _genai_client = genai.Client(
                vertexai=True,
                project=Config.GCP_PROJECT_ID,
                location=Config.GCP_LOCATION
            )
        else:
            _genai_client = genai.Client(api_key=Config.GEMINI_API_KEY)
    return _genai_client
