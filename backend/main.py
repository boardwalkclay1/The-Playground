# backend/main.py

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from generator.orchestrator import run_universal_generator
from assistant import AIAgent

app = FastAPI()
PROJECTS_ROOT = Path("projects")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class GeneratorRequest(BaseModel):
    prompt: str
    project_name: str
    app_type: str = "generic"


class AssistantRequest(BaseModel):
    prompt: str
    project_name: str


@app.post("/api/generator/run")
def api_generator_run(req: GeneratorRequest):
    result = run_universal_generator(
        prompt=req.prompt,
        project_name=req.project_name,
        app_type=req.app_type,
    )

    return {
        "success": result.success,
        "project_name": result.project_name,
        "logs": [{"level": l.level, "message": l.message} for l in result.logs],
        "errors": result.errors,
    }


@app.post("/api/assistant/run")
def api_assistant_run(req: AssistantRequest):
    project_path = PROJECTS_ROOT / req.project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    agent = AIAgent()
    result = agent.run(req.prompt, str(project_path))

    return result


@app.get("/preview/{project_name}", response_class=HTMLResponse)
def preview_project(project_name: str):
    project_path = PROJECTS_ROOT / project_name
    index_path = project_path / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")

    html = index_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html)
