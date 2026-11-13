from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Add relationship to papers
    papers = relationship("Paper", back_populates="project")

class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    title = Column(String, nullable=True)  # paper title detected from the PDF
    file_path = Column(String, nullable=False)
    processing_status = Column(String, default="PENDING") # PENDING, PROCESSED, FAILED
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="papers")