# backend/microcontroller/templates.py
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import time

MCU_ROOT = Path("projects/mcu-sandbox")
LIB_ROOT = MCU_ROOT / "library"
TEMPLATES_ROOT = LIB_ROOT / "templates"
INDEX_PATH = LIB_ROOT / "library_index.json"

LIB_ROOT.mkdir(parents=True, exist_ok=True)
TEMPLATES_ROOT.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_index() -> Dict[str, Any]:
    if not INDEX_PATH.exists():
        return {"templates": []}
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"templates": []}


def _save_index(data: Dict[str, Any]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_templates() -> List[Dict[str, Any]]:
    idx = _load_index()
    return idx.get("templates", [])


def load_template(template_id: str) -> Optional[Dict[str, Any]]:
    idx = _load_index()
    for t in idx.get("templates", []):
        if t.get("id") == template_id:
            folder = TEMPLATES_ROOT / template_id
            files: Dict[str, str] = {}
            if folder.exists():
                for p in folder.rglob("*"):
                    if p.is_file():
                        rel = p.relative_to(folder).as_posix()
                        files[rel] = p.read_text(encoding="utf-8")
            t = dict(t)
            t["files"] = files
            return t
    return None


def save_template(
    template_id: str,
    name: str,
    description: str,
    tags: List[str],
    files: Dict[str, str],
    board_id: Optional[str] = None,
) -> None:
    idx = _load_index()
    templates = idx.get("templates", [])
    templates = [t for t in templates if t.get("id") != template_id]
    meta = {
        "id": template_id,
        "name": name,
        "description": description,
        "tags": tags,
        "board_id": board_id,
        "updated_at": _now_iso(),
    }
    templates.append(meta)
    idx["templates"] = templates
    _save_index(idx)

    folder = TEMPLATES_ROOT / template_id
    if folder.exists():
        for p in folder.rglob("*"):
            if p.is_file():
                p.unlink()
    folder.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        rel_path = rel.lstrip("/").replace("..", "")
        p = folder / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
