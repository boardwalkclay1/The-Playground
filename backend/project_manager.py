# backend/project_manager.py
from pathlib import Path
import shutil
import uuid

PROJECTS_ROOT = Path("projects")
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)


def list_projects():
    projects = []
    for p in sorted(PROJECTS_ROOT.iterdir(), key=lambda x: x.name):
        if p.is_dir():
            projects.append(p.name)
    return projects


def create_project(name: str):
    safe_name = name.strip() or f"project-{uuid.uuid4().hex[:8]}"
    project_path = PROJECTS_ROOT / safe_name
    if project_path.exists():
        return {"success": False, "error": "Project already exists"}
    project_path.mkdir(parents=True, exist_ok=True)
    # create a minimal index.html so preview works
    (project_path / "index.html").write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>"
        + safe_name
        + "</title></head><body><h1>"
        + safe_name
        + "</h1></body></html>",
        encoding="utf-8",
    )
    return {"success": True, "project": safe_name}


def delete_project(name: str):
    project_path = PROJECTS_ROOT / name
    if not project_path.exists():
        return {"success": False, "error": "Project not found"}
    shutil.rmtree(project_path)
    return {"success": True}


def duplicate_project(name: str, new_name: str = None):
    src = PROJECTS_ROOT / name
    if not src.exists():
        return {"success": False, "error": "Source project not found"}
    dest_name = new_name or f"{name}-copy-{uuid.uuid4().hex[:6]}"
    dest = PROJECTS_ROOT / dest_name
    if dest.exists():
        return {"success": False, "error": "Destination already exists"}
    shutil.copytree(src, dest)
    return {"success": True, "project": dest_name}


def rename_project(old_name: str, new_name: str):
    src = PROJECTS_ROOT / old_name
    dest = PROJECTS_ROOT / new_name
    if not src.exists():
        return {"success": False, "error": "Source project not found"}
    if dest.exists():
        return {"success": False, "error": "Destination already exists"}
    src.rename(dest)
    return {"success": True, "project": new_name}
