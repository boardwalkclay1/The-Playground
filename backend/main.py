# backend/main.py
"""
Unified FastAPI Application (Upgraded)
--------------------------------------

Integrates:
- Universal Generator (fused planner)
- Assistant (project-optional, fused intelligence)
- AI Panel Pro (wiring/code/image)
- File operations
- Terminal operations
- Project manager
- MCU router
- Static frontend (Playground + MCU Lab)
"""

from pathlib import Path
from typing import Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from generator.orchestrator import run_universal_generator
from assistant.assistant_api import router as assistant_router
from assistant.ai_panel_api import router as ai_panel_router

# ---------------------------------------------------------
# OPTIONAL MODULES (SOFT IMPORTS)
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------
app = FastAPI(title="Boardwalk Playground Studio")

ROOT = Path.cwd()
FRONTEND_ROOT = ROOT / "frontend"
STATIC_ROOT = FRONTEND_ROOT / "static"
PROJECTS_ROOT = ROOT / "projects"
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_methods=["*"],
  allow_headers=["*"],
)

if STATIC_ROOT.exists():
  app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# ROOT / INDEX
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def root_index():
  index_path = FRONTEND_ROOT / "index.html"
  if not index_path.exists():
    return HTMLResponse("<h1>Boardwalk Playground Studio</h1><p>frontend/index.html not found.</p>", status_code=200)
  return HTMLResponse(index_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------
# GENERATOR
# ---------------------------------------------------------
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
    "logs": [
      {"level": l.level, "message": l.message}
      for l in getattr(result, "logs", [])
    ],
    "errors": getattr(result, "errors", []),
  }


# ---------------------------------------------------------
# ASSISTANT (FUSED)
# ---------------------------------------------------------
app.include_router(assistant_router, prefix="/api")


# ---------------------------------------------------------
# AI PANEL PRO (FUSED)
# ---------------------------------------------------------
app.include_router(ai_panel_router, prefix="/api")


# ---------------------------------------------------------
# PREVIEW
# ---------------------------------------------------------
@app.get("/preview/{project_name}", response_class=HTMLResponse)
def preview_project(project_name: str):
  project_path = PROJECTS_ROOT / project_name
  index_path = project_path / "index.html"

  if not index_path.exists():
    raise HTTPException(status_code=404, detail="index.html not found")

  html = index_path.read_text(encoding="utf-8")
  return HTMLResponse(content=html)


# ---------------------------------------------------------
# PROJECT MANAGER
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# FILES ROUTER
# ---------------------------------------------------------
if files_router:
  app.include_router(files_router, prefix="/api")


# ---------------------------------------------------------
# TERMINAL ROUTER
# ---------------------------------------------------------
if terminal_router:
  app.include_router(terminal_router, prefix="/api")


# ---------------------------------------------------------
# MCU ROUTER
# ---------------------------------------------------------
if mcu_router:
  app.include_router(mcu_router)
