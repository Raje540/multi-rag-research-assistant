import os
import shutil
import traceback
from collections import Counter
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Paper, Project
from backend.services.pdf_service import process_pdf_to_chunks, extract_paper_title
# NEW IMPORT: For storing vectors into local ChromaDB
from backend.services.vector_service import store_chunks_in_vector_db, delete_paper_chunks

router = APIRouter(
    prefix="/api/papers",
    tags=["Papers"]
)

# Ensure upload directory exists
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_all_papers(db: Session = Depends(get_db)):
    """Fetch all papers saved in the database."""
    papers = db.query(Paper).all()
    return {
        "papers": [
            {
                "id": p.id,
                "project_id": p.project_id,
                "filename": p.filename,
                "title": getattr(p, "title", None),
                "file_path": p.file_path,
                "processing_status": p.processing_status
            }
            for p in papers
        ]
    }

@router.post("/upload")
async def upload_paper(
    project_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Verify project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save file locally safely
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)

    # Save metadata entry to SQLite
    new_paper = Paper(
        project_id=project_id,
        filename=file.filename,
        file_path=file_location,
        processing_status="UPLOADED"
    )
    db.add(new_paper)
    db.commit()
    db.refresh(new_paper)

    return {
        "message": f"Successfully uploaded {file.filename}",
        "paper_id": new_paper.id
    }

@router.delete("/{paper_id}")
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """
    Delete one paper record and its indexed chunks (use this to remove duplicates).
    The PDF file in data/uploads is NOT deleted, because duplicate records can
    share the same file.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in database.")

    project_id = paper.project_id
    filename = paper.filename

    try:
        delete_paper_chunks(project_id, paper.id)
    except Exception as exc:
        print(f"[WARNING] Could not remove vectors for paper {paper_id}: {exc}")

    db.delete(paper)
    db.commit()
    _CHUNK_CACHE.pop(paper_id, None)

    return {
        "message": f"Deleted paper {paper_id} ({filename}) and its indexed chunks.",
        "paper_id": paper_id,
        "project_id": project_id
    }

@router.get("/{paper_id}/extract")
def extract_paper_text(paper_id: int, db: Session = Depends(get_db)):
    # 1. Look up paper record
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in database.")

    # 2. Verify file exists on local storage
    if not os.path.exists(paper.file_path):
        raise HTTPException(status_code=404, detail=f"PDF file missing at path: {paper.file_path}")

    try:
        # 3. Process PDF safely with memory guardrail (max 30 pages)
        chunks = process_pdf_to_chunks(paper.file_path, chunk_size=1000, overlap=200, max_pages=30)

        # 3b. Detect the paper title (used in citations)
        paper_title = extract_paper_title(paper.file_path)

        # 4. NEW STEP: Convert chunks into vector embeddings and store in ChromaDB
        total_vectors = store_chunks_in_vector_db(
            project_id=paper.project_id,
            paper_id=paper.id,
            chunks=chunks,
            paper_title=paper_title
        )

        # 5. Update paper status in DB upon success
        paper.title = paper_title
        paper.processing_status = "EXTRACTED_AND_INDEXED"
        db.commit()

        # Keep the /chunks cache in step with what was just indexed
        _CHUNK_CACHE[paper.id] = (os.path.getmtime(paper.file_path), chunks)

        # Extract sample preview safely
        sample_chunk = chunks[0]["text"] if chunks else "No text extracted."

        return {
            "message": f"Successfully extracted text from {paper.filename}",
            "paper_id": paper.id,
            "total_chunks_created": len(chunks),
            "total_vectors_indexed": total_vectors,
            "sample_first_chunk": sample_chunk,
            "title": paper_title,
            "category_counts": dict(Counter(c.get("category", "Other") for c in chunks)),
            "sections_found": sorted({c.get("section", "unknown") for c in chunks})
        }

    except ValueError as ve:
        # Gracefully handle safety limit caps without crashing the backend server
        print(f"\n[SAFETY LIMIT TRIGGERED]: {str(ve)}\n")
        raise HTTPException(status_code=400, detail=str(ve))

    except Exception as e:
        # Print complete traceback to terminal for rapid diagnosis
        print("\n--- EXTRACTION ERROR ---")
        traceback.print_exc()
        print("------------------------\n")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {type(e).__name__} - {str(e)}")

# Cache so the dashboard metric (which calls /chunks on every page refresh)
# doesn't re-parse the PDF each time. Refreshes automatically if the file changes.
_CHUNK_CACHE = {}


@router.get("/{paper_id}/chunks")
def get_paper_chunks(paper_id: int, db: Session = Depends(get_db)):
    """
    Return the text chunks of a paper (the same chunks that are indexed in ChromaDB).
    Fixes the 404 on GET /api/papers/{id}/chunks that the Streamlit frontend calls.
    """
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found in database.")

    if not os.path.exists(paper.file_path):
        raise HTTPException(status_code=404, detail=f"PDF file missing at path: {paper.file_path}")

    try:
        mtime = os.path.getmtime(paper.file_path)
        cached = _CHUNK_CACHE.get(paper.id)
        if cached and cached[0] == mtime:
            chunks = cached[1]
        else:
            chunks = process_pdf_to_chunks(paper.file_path, chunk_size=1000, overlap=200, max_pages=30)
            _CHUNK_CACHE[paper.id] = (mtime, chunks)
        return {
            "paper_id": paper.id,
            "filename": paper.filename,
            "total_chunks": len(chunks),
            "chunks": chunks
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chunk retrieval failed: {type(e).__name__} - {str(e)}")