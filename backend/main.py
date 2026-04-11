# backend/main.py
"""
Unified FastAPI Application
---------------------------

This app integrates:
- Universal Generator
- Assistant (project-aware, policy-driven)
- File operations
- Terminal operations
- Project manager
- Cloudflare ops
- GitHub ops
- MCU router (optional)
- AI Panel Pro
"""

from pathlib import Path
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uuid

# Core modules
from generator.orchestrator import run_universal_generator
from assistant.assistant_api import router as assistant_router

# Optional modules
try:
    from project_manager import (
        list_projects,
        create_project,
        delete_project,
        duplicate_project,
        rename_project,
    )
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

try:
    from microcontroller.api import router as mcu_router
except Exception:
    mcu_router = None


# ============================================================
# APP
# ============================================================

app = FastAPI()
PROJECTS_ROOT = Path("projects")
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files served by frontend server (5173)


# ============================================================
# MODELS
# ============================================================

class GeneratorRequest(BaseModel):
    prompt: str
    project_name: str
    app_type: str = "generic"


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


class AIPanelRequest(BaseModel):
    prompt: str
    session_id: str


class AIPanelImageRequest(AIPanelRequest):
    style: str
    resolution: str


# ============================================================
# IN-MEMORY CONVERSATION STORE
# ============================================================

CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}


def get_history(session_id: str) -> List[Dict[str, str]]:
    return CONVERSATIONS.get(session_id, [])


def append_history(session_id: str, role: str, content: str) -> None:
    CONVERSATIONS.setdefault(session_id, []).append({"role": role, "content": content})
    CONVERSATIONS[session_id] = CONVERSATIONS[session_id][-30:]


# ============================================================
# GENERATOR
# ============================================================

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


# ============================================================
# ASSISTANT ROUTER
# ============================================================

app.include_router(assistant_router, prefix="/api")


# ============================================================
# PREVIEW
# ============================================================

@app.get("/preview/{project_name}", response_class=HTMLResponse)
def preview_project(project_name: str):
    project_path = PROJECTS_ROOT / project_name
    index_path = project_path / "index.html"

    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")

    html = index_path.read_text(encoding="utf-8")
    return HTMLResponse(content=html)


# ============================================================
# PROJECT MANAGER
# ============================================================

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


# ============================================================
# FILES ROUTER
# ============================================================

if files_router:
    app.include_router(files_router, prefix="/api")


# ============================================================
# TERMINAL ROUTER
# ============================================================

if terminal_router:
    app.include_router(terminal_router, prefix="/api")


# ============================================================
# MCU ROUTER (FIXED)
# ============================================================

if mcu_router:
    # router already has prefix="/mcu"
    app.include_router(mcu_router)


# ============================================================
# AI PANEL PRO
# ============================================================

@app.post("/ai/wiring")
def ai_wiring(req: AIPanelRequest):
    append_history(req.session_id, "user", f"[WIRING] {req.prompt}")
    text = "[WIRING RESPONSE HERE]"
    append_history(req.session_id, "assistant", text)
    return {"text": text}


@app.post("/ai/code")
def ai_code(req: AIPanelRequest):
    append_history(req.session_id, "user", f"[CODE] {req.prompt}")
    text = "[CODE RESPONSE HERE]"
    append_history(req.session_id, "assistant", text)
    return {"text": text}


@app.post("/ai/image")
def ai_image(req: AIPanelImageRequest):
    append_history(
        req.session_id,
        "user",
        f"[IMAGE] {req.prompt} | style={req.style} | res={req.resolution}",
    )

    image_url = f"/static/generated/{uuid.uuid4()}.png"
    desc = f"Generated image in style '{req.style}' at {req.resolution}."

    append_history(req.session_id, "assistant", desc)
    return {"image_url": image_url, "description": desc}
