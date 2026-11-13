from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.rag_service import (
    retrieve_context_for_query, 
    generate_rag_prompt,
    generate_answer_with_llm
)

router = APIRouter(
    prefix="/api/chat",
    tags=["Research Chat"]
)

class QueryRequest(BaseModel):
    project_id: int
    query: str
    top_k: int = 4

@router.post("/query")
def query_research_assistant(request: QueryRequest):
    """
    Executes similarity search on ChromaDB, builds context-grounded prompt,
    generates an answer using the LLM, and returns retrieved evidence blocks with page citations.
    """
    try:
        evidence = retrieve_context_for_query(
            project_id=request.project_id,
            query=request.query,
            top_k=request.top_k
        )
        
        prompt = generate_rag_prompt(query=request.query, evidence_chunks=evidence)
        answer = generate_answer_with_llm(prompt=prompt, evidence_chunks=evidence)
        
        return {
            "query": request.query,
            "project_id": request.project_id,
            "answer": answer,
            "evidence_count": len(evidence),
            "evidence": evidence,
            "formatted_prompt": prompt
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")