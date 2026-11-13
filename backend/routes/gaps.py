import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Paper
from backend.services.gap_service import detect_gaps, load_gaps
from backend.services.validation_service import validate_project

router = APIRouter(
    prefix="/api/gaps",
    tags=["Gap Detection"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/detect/{project_id}")
def detect(project_id: int, use_llm: bool = True, db: Session = Depends(get_db)):
    """Find the gaps the authors state themselves (limitations, open issues, future work) in every indexed paper."""
    papers = db.query(Paper).filter(
        Paper.project_id == project_id,
        Paper.processing_status == "EXTRACTED_AND_INDEXED",
    ).order_by(Paper.id).all()
    if not papers:
        raise HTTPException(status_code=400, detail="No indexed papers in this project yet.")
    try:
        return detect_gaps(
            project_id,
            [{"id": p.id, "title": p.title or p.filename} for p in papers],
            use_llm=use_llm,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gap detection failed: {type(e).__name__} - {str(e)}")


@router.get("/validate/{project_id}")
def validate(project_id: int, db: Session = Depends(get_db)):
    """Check every saved gap against the OTHER papers: does another paper also call it open, or say it works on it?"""
    papers = db.query(Paper).filter(
        Paper.project_id == project_id,
        Paper.processing_status == "EXTRACTED_AND_INDEXED",
    ).order_by(Paper.id).all()
    try:
        return validate_project(project_id, [{"id": p.id, "title": p.title or p.filename} for p in papers])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Gap validation failed: {type(e).__name__} - {str(e)}")


@router.get("/{project_id}")
def saved_gaps(project_id: int):
    """The gaps saved by the last detection run (empty list if none)."""
    data = load_gaps(project_id)
    return data or {"project_id": project_id, "gaps": [], "papers_without_gaps": [], "total_papers": 0}