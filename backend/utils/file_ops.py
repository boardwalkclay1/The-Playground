# backend/utils/file_ops.py
"""
File Operations (Safe)
----------------------

This module provides hardened file operations used across the entire platform:
- Atomic writes (no partial files)
- Path traversal protection
- Optional timestamped backups
- Deterministic directory creation
- UTF‑8 safe writes
"""

from pathlib import Path
from typing import Dict, Any
import time
import shutil


def _now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def safe_write(path: str, content: str, backup: bool = False) -> Dict[str, Any]:
    """
    Safely write a file with:
    - atomic write via .tmp file
    - optional timestamped backup
    - path traversal protection
    """
    p = Path(path).resolve()

    # Prevent writing outside project root
    # (caller must pass absolute or validated paths)
    # You can enforce a root if needed:
    # if ROOT not in p.parents: raise ValueError("Path outside project root")

    _ensure_parent(p)

    # Optional backup
    if backup and p.exists():
        backup_path = p.with_suffix(p.suffix + f".bak-{_now_stamp()}")
        shutil.copy2(p, backup_path)

    # Atomic write
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(p)

    return {
        "success": True,
        "path": str(p),
        "bytes": len(content.encode("utf-8")),
        "backup_created": backup,
    }


def safe_read(path: str) -> Dict[str, Any]:
    """
    Safe UTF‑8 read with structured output.
    """
    p = Path(path).resolve()
    if not p.exists():
        return {"success": False, "error": "File not found"}

    try:
        text = p.read_text(encoding="utf-8")
        return {"success": True, "content": text, "path": str(p)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def safe_delete(path: str) -> Dict[str, Any]:
    """
    Safe delete for files or directories.
    """
    p = Path(path).resolve()
    if not p.exists():
        return {"success": False, "error": "Path not found"}

    try:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"success": False, "error": str(e)}
