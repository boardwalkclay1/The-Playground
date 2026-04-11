from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from generator.orchestrator import run_universal_generator
from assistant import AIAgent

# Modular imports
try:
    from project_manager import list_projects, create_project, delete_project, duplicate_project, rename_project
except Exception:
    list_projects = lambda: []
    create_project = lambda name: {"success": False, "error": "project_manager not installed"}
    delete_project = lambda name: {"success": False, "error": "project_manager not installed"}
    duplicate_project = lambda name, new_name=None: {"success": False, "error": "project_manager not installed"}
    rename_project = lambda old, new: {"success": False, "error": "project_manager not installed"}

try:
    from files_api import router as files_router
except Exception:
    files_router = None

try:
    from terminal_api import router as terminal_router
except Exception:
    terminal_router = None

# NEW: MCU API router
try:
    from microcontroller.api import router as mcu_router
except Exception:
    mcu_router = None


app = FastAPI()
PROJECTS_ROOT = Path("projects")
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (CSS, JS, MCU Lab, assets)
app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------
# MODELS
# -----------------------------
class GeneratorRequest(BaseModel):
    prompt: str
    project_name: str
    app_type: str = "generic"


class AssistantRequest(BaseModel):
    prompt: str
    project_name: str


class ProjectCreateRequest(BaseModel):
    name: str


class ProjectNameRequest(BaseModel):
    name: str


class ProjectDuplicateRequest(BaseModel):
    name: str
    new_name: str | None = None


class ProjectRenameRequest(BaseModel):
    old: str
    new: str


class FileReadRequest(BaseModel):
    project_name: str
    path: str


class FileWriteRequest(BaseModel):
    project_name: str
    path: str
    content: str


class TerminalRequest(BaseModel):
    project_name: str
    command: str


# -----------------------------
# GENERATOR
# -----------------------------
@app.post("/api/generator/run")
def api_generator_run(req: GeneratorRequest):
    result = run_universal_generator(
        prompt=req.prompt,
        project_name=req.project_name,
        app_type=req.app_type,
    )

    return {
        "success": getattr(result, "success", False),
        "project_name": getattr(result, "project_name", req.project_name),
        "logs": [{"level": l.level, "message": l.message} for l in getattr(result, "logs", [])],
        "errors": getattr(result, "errors", []),
    }


# -----------------------------
# ASSISTANT
# -----------------------------
@app.post("/api/assistant/run")
def api_assistant_run(req: AssistantRequest):
    project_path = PROJECTS_ROOT / req.project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    agent = AIAgent()
    result = agent.run(req.prompt, str(project_path))
    return result


# -----------------------------
# PREVIEW
# -----------------------------
@app.get("/preview/{project_name}", response_class=HTMLResponse)
def preview_project(project_name: str):
    project_path = PROJECTS_ROOT / project_name
    index_path = project_path / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")

    html = index_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


# -----------------------------
# PROJECT MANAGER
# -----------------------------
@app.get("/api/projects")
def api_list_projects():
    try:
        return {"success": True, "projects": list_projects()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/projects/create")
def api_create_project(payload: ProjectCreateRequest):
    try:
        return create_project(payload.name)
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/projects/delete")
def api_delete_project(payload: ProjectNameRequest):
    try:
        return delete_project(payload.name)
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/projects/duplicate")
def api_duplicate_project(payload: ProjectDuplicateRequest):
    try:
        return duplicate_project(payload.name, payload.new_name)
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/projects/rename")
def api_rename_project(payload: ProjectRenameRequest):
    try:
        return rename_project(payload.old, payload.new)
    except Exception as e:
        return {"success": False, "error": str(e)}


# -----------------------------
# FILES ROUTER
# -----------------------------
if files_router:
    app.include_router(files_router, prefix="/api")
else:
    # fallback inline implementation
    @app.get("/api/files/tree/{project_name}")
    def api_files_tree(project_name: str):
        project_path = PROJECTS_ROOT / project_name
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        def build_tree(base: Path, root: Path):
            items = []
            for p in sorted(base.iterdir(), key=lambda x: x.name):
                rel = p.relative_to(root).as_posix()
                if p.is_dir():
                    items.append({"type": "dir", "name": p.name, "path": rel, "children": build_tree(p, root)})
                else:
                    items.append({"type": "file", "name": p.name, "path": rel})
            return items

        return {"success": True, "tree": build_tree(project_path, project_path)}

    @app.post("/api/files/read")
    def api_files_read(payload: FileReadRequest):
        project_path = PROJECTS_ROOT / payload.project_name
        file_path = project_path / payload.path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        return {"success": True, "content": file_path.read_text(encoding="utf-8")}

    @app.post("/api/files/write")
    def api_files_write(payload: FileWriteRequest):
        project_path = PROJECTS_ROOT / payload.project_name
        file_path = project_path / payload.path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(payload.content, encoding="utf-8")
        return {"success": True}

    @app.post("/api/files/delete")
    def api_files_delete(payload: FileReadRequest):
        project_path = PROJECTS_ROOT / payload.project_name
        file_path = project_path / payload.path
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        return {"success": True}


# -----------------------------
# TERMINAL ROUTER
# -----------------------------
if terminal_router:
    app.include_router(terminal_router, prefix="/api")
else:
    @app.post("/api/terminal/run")
    def api_terminal_run(req: TerminalRequest):
        project_path = PROJECTS_ROOT / req.project_name
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        agent = AIAgent()
        result = agent.run(f"run command: {req.command}", str(project_path))
        return result


# -----------------------------
# MCU ROUTER (NEW)
# -----------------------------
if mcu_router:
    app.include_router(mcu_router, prefix="/mcu")
else:
    raise RuntimeError("microcontroller.api router missing — MCU system not installed")
