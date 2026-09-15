from fastapi import FastAPI
from backend.routes.projects import router as projects_router

app = FastAPI(
    title="Multi-RAG Research Assistant",
    description="Evidence-Traceable Research Gap Validation System",
    version="1.0.0"
)

app.include_router(projects_router)


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