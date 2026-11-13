import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Paper
from backend.services.evidence_service import analyze_paper, load_cached, debug_paper

router = APIRouter(
    prefix="/api/evidence",
    tags=["Evidence Analysis"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/analyze/paper/{paper_id}")
def analyze_one_paper(paper_id: int, use_llm: bool = True, db: Session = Depends(get_db)):
    """
    Build the evidence summary (Methodology, Dataset, Results, Limitations) for ONE paper.
    Can take a minute or two with the local model, so the frontend calls it paper by paper.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in database.")
    if paper.processing_status != "EXTRACTED_AND_INDEXED":
        raise HTTPException(status_code=400, detail="Paper is not indexed yet. Run extract first.")

    try:
        return analyze_paper(
            project_id=paper.project_id,
            paper_id=paper.id,
            title=paper.title or paper.filename,
            use_llm=use_llm,
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Evidence analysis failed: {type(e).__name__} - {str(e)}")


@router.get("/{project_id}")
def get_project_evidence(project_id: int, db: Session = Depends(get_db)):
    """Return the saved evidence analysis for every indexed paper of a project."""
    papers = db.query(Paper).filter(
        Paper.project_id == project_id,
        Paper.processing_status == "EXTRACTED_AND_INDEXED",
    ).all()

    results = []
    for p in papers:
        cached = load_cached(p.id)
        if cached:
            results.append(cached)

    return {
        "project_id": project_id,
        "total_papers": len(papers),
        "analyzed_papers": len(results),
        "papers": results,
    }


@router.get("/debug/{paper_id}/{dimension}")
def debug_evidence(paper_id: int, dimension: str, db: Session = Depends(get_db)):
    """Shows which stored chunks (page, section, category) a dimension reads. Used to find why a cell is wrong."""
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in database.")
    try:
        return debug_paper(paper.project_id, paper.id, dimension)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__} - {str(e)}")