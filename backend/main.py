from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

# Database and Model Imports
from backend.database import engine, Base
from backend import models

# Route Imports
from backend.routes.projects import router as projects_router
from backend.routes.papers import router as papers_router
from backend.routes.chat import router as chat_router
from backend.routes.evidence import router as evidence_router

# Safely import gaps_router if available, avoiding ModuleNotFoundError crashes
try:
    from backend.routes.gaps import router as gaps_router
    HAS_GAPS_ROUTER = True
except ModuleNotFoundError:
    HAS_GAPS_ROUTER = False

# Safely import the final report route the same way
try:
    from backend.routes.report import router as report_router
    HAS_REPORT_ROUTER = True
except ModuleNotFoundError:
    HAS_REPORT_ROUTER = False

# Create database tables
Base.metadata.create_all(bind=engine)


def _add_missing_columns():
    """
    create_all() does not add new columns to tables that already exist.
    Add the 'title' column to an existing papers table so old databases keep working.
    """
    columns = [c["name"] for c in inspect(engine).get_columns("papers")]
    if "title" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE papers ADD COLUMN title VARCHAR"))


_add_missing_columns()

app = FastAPI(
    title="Multi-RAG Research Assistant",
    description="Evidence-Traceable Research Gap Validation System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Core Route Modules
app.include_router(projects_router)
app.include_router(papers_router)
app.include_router(chat_router)    # Endpoint: /api/chat/query
app.include_router(evidence_router)  # Endpoints: /api/evidence/...

# Register Gaps Route Module if module exists
if HAS_GAPS_ROUTER:
    app.include_router(gaps_router)  # Endpoint: /api/gaps/detect/{project_id}

if HAS_REPORT_ROUTER:
    app.include_router(report_router)  # Endpoint: /api/report/{project_id}


@app.get("/")
def root():
    return {
        "message": "Multi-RAG Research Assistant API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }