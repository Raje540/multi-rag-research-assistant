import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Paper, Project
from backend.services.report_service import build_report

router = APIRouter(
    prefix="/api/report",
    tags=["Final Report"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/{project_id}")
def final_report(project_id: int, db: Session = Depends(get_db)):
    """Build the research report from the saved Evidence Analysis, Gap Detection and Gap Validation results."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    papers = db.query(Paper).filter(
        Paper.project_id == project_id,
        Paper.processing_status == "EXTRACTED_AND_INDEXED",
    ).order_by(Paper.id).all()
    if not papers:
        raise HTTPException(status_code=400, detail="No indexed papers in this project yet.")
    try:
        return build_report(
            {"id": project.id, "name": project.name, "domain": project.domain, "description": project.description},
            [{"id": p.id, "title": p.title or p.filename} for p in papers],
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report failed: {type(e).__name__} - {str(e)}")