# backend/files_api.py
# Hardened, upgraded, safe, production‑ready file API

from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
import shutil
import json

router = APIRouter()
PROJECTS_ROOT = Path("projects")


# ---------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------

def _safe_project(project_name: str) -> Path:
    p = PROJECTS_ROOT / project_name
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _safe_path(project: Path, rel_path: str) -> Path:
    full = (project / rel_path).resolve()
    if not str(full).startswith(str(project.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    return full


def build_tree(base: Path, root: Path) -> List[Dict[str, Any]]:
    items = []
    for p in sorted(base.iterdir(), key=lambda x: x.name.lower()):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            items.append({
                "type": "dir",
                "name": p.name,
                "path": rel,
                "children": build_tree(p, root),
            })
        else:
            items.append({
                "type": "file",
                "name": p.name,
                "path": rel,
            })
    return items


# ---------------------------------------------------------
# FILE TREE
# ---------------------------------------------------------

@router.get("/files/tree/{project_name}")
def api_files_tree(project_name: str):
    project = _safe_project(project_name)
    tree = build_tree(project, project)
    return {"success": True, "tree": tree}


# ---------------------------------------------------------
# READ FILE
# ---------------------------------------------------------

@router.post("/files/read")
def api_files_read(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    rel_path = payload.get("path")

    if not project_name or not rel_path:
        raise HTTPException(status_code=400, detail="Missing parameters")

    project = _safe_project(project_name)
    file_path = _safe_path(project, rel_path)

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")

    return {"success": True, "content": content}


# ---------------------------------------------------------
# WRITE FILE
# ---------------------------------------------------------

@router.post("/files/write")
def api_files_write(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    rel_path = payload.get("path")
    content = payload.get("content", "")

    if not project_name or not rel_path:
        raise HTTPException(status_code=400, detail="Missing parameters")

    project = _safe_project(project_name)
    file_path = _safe_path(project, rel_path)

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Write failed: {e}")

    return {"success": True, "path": rel_path}


# ---------------------------------------------------------
# DELETE FILE OR FOLDER
# ---------------------------------------------------------

@router.post("/files/delete")
def api_files_delete(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    rel_path = payload.get("path")

    if not project_name or not rel_path:
        raise HTTPException(status_code=400, detail="Missing parameters")

    project = _safe_project(project_name)
    file_path = _safe_path(project, rel_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")

    return {"success": True}


# ---------------------------------------------------------
# MOVE / RENAME
# ---------------------------------------------------------

@router.post("/files/move")
def api_files_move(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    src = payload.get("src")
    dst = payload.get("dst")

    if not project_name or not src or not dst:
        raise HTTPException(status_code=400, detail="Missing parameters")

    project = _safe_project(project_name)
    src_path = _safe_path(project, src)
    dst_path = _safe_path(project, dst)

    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        src_path.rename(dst_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Move failed: {e}")

    return {"success": True, "from": src, "to": dst}
