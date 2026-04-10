# backend/files_api.py
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
import shutil

router = APIRouter()
PROJECTS_ROOT = Path("projects")


def build_tree(base: Path, root: Path) -> List[Dict[str, Any]]:
    items = []
    for p in sorted(base.iterdir(), key=lambda x: x.name):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            items.append(
                {
                    "type": "dir",
                    "name": p.name,
                    "path": rel,
                    "children": build_tree(p, root),
                }
            )
        else:
            items.append({"type": "file", "name": p.name, "path": rel})
    return items


@router.get("/files/tree/{project_name}")
def api_files_tree(project_name: str):
    project_path = PROJECTS_ROOT / project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    tree = build_tree(project_path, project_path)
    return {"success": True, "tree": tree}


@router.post("/files/read")
def api_files_read(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    path = payload.get("path")
    project_path = PROJECTS_ROOT / project_name
    file_path = project_path / path
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    content = file_path.read_text(encoding="utf-8")
    return {"success": True, "content": content}


@router.post("/files/write")
def api_files_write(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    path = payload.get("path")
    content = payload.get("content", "")
    project_path = PROJECTS_ROOT / project_name
    file_path = project_path / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return {"success": True, "path": path}


@router.post("/files/delete")
def api_files_delete(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    path = payload.get("path")
    project_path = PROJECTS_ROOT / project_name
    file_path = project_path / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if file_path.is_dir():
        shutil.rmtree(file_path)
    else:
        file_path.unlink()
    return {"success": True}


@router.post("/files/move")
def api_files_move(payload: Dict[str, str]):
    project_name = payload.get("project_name")
    src = payload.get("src")
    dst = payload.get("dst")
    project_path = PROJECTS_ROOT / project_name
    src_path = project_path / src
    dst_path = project_path / dst
    if not src_path.exists():
        raise HTTPException(status_code=404, detail="Source not found")
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    src_path.rename(dst_path)
    return {"success": True, "from": src, "to": dst}
