from fastapi import FastAPI

app = FastAPI(
    title="Multi-RAG Research Assistant",
    description="Evidence-Traceable Research Gap Validation System",
    version="1.0.0"
)


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