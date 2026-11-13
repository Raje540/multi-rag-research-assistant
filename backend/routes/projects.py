from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from backend.database import SessionLocal
from backend.models import Project

router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"]
)


# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class ProjectCreate(BaseModel):
    project_name: str
    research_domain: str
    description: str = ""


@router.get("/")
def get_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    return {
        "message": "Project API is working",
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "domain": p.domain,
                "description": p.description,
                "created_at": p.created_at
            }
            for p in projects
        ]
    }


@router.post("/")
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    new_project = Project(
        name=project.project_name,
        domain=project.research_domain,
        description=project.description
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "message": "Project created successfully",
        "id": new_project.id,
        "project_name": new_project.name,
        "research_domain": new_project.domain,
        "description": new_project.description
    }