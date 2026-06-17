from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class LessonStub(BaseModel):
    index: int
    title: str

class ModuleStub(BaseModel):
    index: int
    title: str
    learning_objectives: List[str]
    lessons: List[LessonStub]

class CourseOutline(BaseModel):
    title: str
    description: str
    total_modules: int
    modules: List[ModuleStub]

class TableData(BaseModel):
    headers: List[str]
    rows: List[List[str]]

class LessonSegment(BaseModel):
    slide_index: int
    slide_title: str
    slide_bullets: List[str]
    narration: str = ""
    slide_type: Literal["text", "photo", "table"] = "text"
    image_query: Optional[str] = None   # Used when slide_type == "photo"
    table_data: Optional[TableData] = None  # Used when slide_type == "table"

class LessonContent(BaseModel):
    module_index: int
    lesson_index: int
    title: str
    segments: List[LessonSegment]
    key_takeaways: List[str]
    lesson_essay: Optional[str] = ""  # 250-300 word prose summary shown beneath the slide deck

class SegmentTiming(BaseModel):
    slide_index: int
    start_time: float
    duration: float

class LessonAudio(BaseModel):
    lesson_id: str
    audio_file: str
    timing_manifest: List[SegmentTiming]

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: str

class Quiz(BaseModel):
    module_index: int
    questions: List[QuizQuestion]

class Flashcard(BaseModel):
    front: str
    back: str

class FlashcardDeck(BaseModel):
    module_index: int
    cards: List[Flashcard]

class FullCourseContent(BaseModel):
    lessons: Optional[List[LessonContent]] = Field(default_factory=list)
    quizzes: Optional[List[Quiz]] = Field(default_factory=list)
    flashcards: Optional[List[FlashcardDeck]] = Field(default_factory=list)

class GeneratedCourse(BaseModel):
    course_id: str
    outline: CourseOutline
    content: Optional[FullCourseContent] = None
    audio: Optional[List[LessonAudio]] = None
    slide_path: Optional[str] = None
    quiz_pdf_path: Optional[str] = None
    summary_pdf_path: Optional[str] = None
