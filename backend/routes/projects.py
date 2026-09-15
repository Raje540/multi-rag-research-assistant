from fastapi import APIRouter

router = APIRouter(
    prefix="/api/projects",
    tags=["Projects"]
)


@router.get("/")
def get_projects():
    return {
        "message": "Project API is working"
    }


@router.post("/")
def create_project(project_name: str, research_domain: str):
    return {
        "message": "Project created successfully",
        "project_name": project_name,
        "research_domain": research_domain
    }