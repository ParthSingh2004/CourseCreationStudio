from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime, timezone
from database import Base

class CourseModel(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    json_content = Column(Text, nullable=True) # Will store the full GeneratedCourse JSON dump
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

