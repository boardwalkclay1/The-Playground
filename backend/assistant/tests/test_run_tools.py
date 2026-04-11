# backend/utils/file_ops.py
"""
Hardened File Operations (Platform‑Wide Standard)
-------------------------------------------------

This module provides the *lowest‑level* safe file operations used across the
entire platform:

- Path traversal protection
- Atomic writes (temp file → replace)
- Optional timestamped backups
- Deterministic directory creation
- UTF‑8 safe reads/writes
- Structured return payloads
- Never throws exceptions
"""

from pathlib import Path
from typing import Dict, Any, Optional
import time
import shutil
import tempfile
import json


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _now_stamp() -> str:
    return time.strftime("%Y%m%dT%H%M%S", time.gmtime())


def _ensure_parent(path: Path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _atomic_write(path: Path, content: str) -> None:
    """
    Atomic write using a temp file in the same directory.
    """
    _ensure_parent(path)

    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    tmp_path = Path(tmp)

    try:
        with open(fd, "wb") as f:
            f.write(content.encode("utf-8"))

        # Atomic replace
        tmp_path.replace(path)

    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass


def _create_backup(path: Path) -> Optional[str]:
    """
    Create timestamped backup if file exists.
    """
    try:
        if not path.exists():
            return None
        bak = path.with_name(path.name + f".bak-{_now_stamp()}")
        shutil.copy2(path, bak)
        return str(bak)
    except Exception:
        return None


def _resolve(path: str, root: Optional[str] = None) -> Path:
    """
    Resolve path and enforce optional project root.
    """
    p = Path(path).resolve()

    if root:
        root_p = Path(root).resolve()
        if not str(p).startswith(str(root_p)):
            raise PermissionError("Path outside project root is not allowed")

    return p


# ============================================================
# PUBLIC API
# ============================================================

def safe_write(path: str, content: str, backup: bool = False, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely write a file with:
    - atomic write
    - optional timestamped backup
    - optional root enforcement
    """
    try:
        p = _resolve(path, root)

        backup_path = None
        if backup and p.exists():
            backup_path = _create_backup(p)

        _atomic_write(p, content)

        return {
            "success": True,
            "path": str(p),
            "bytes": len(content.encode("utf-8")),
            "backup": backup_path,
        }

    except PermissionError as pe:
        return {"success": False, "error": str(pe), "code": "PATH_OUTSIDE_ROOT"}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "WRITE_ERROR"}


def safe_read(path: str, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Safe UTF‑8 read with structured output.
    """
    try:
        p = _resolve(path, root)

        if not p.exists():
            return {"success": False, "error": "File not found", "code": "NOT_FOUND"}

        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            return {"success": True, "content": text, "path": str(p)}
        except Exception as e:
            return {"success": False, "error": str(e), "code": "READ_ERROR"}

    except PermissionError as pe:
        return {"success": False, "error": str(pe), "code": "PATH_OUTSIDE_ROOT"}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "UNKNOWN"}


def safe_delete(path: str, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Safe delete for files or directories.
    """
    try:
        p = _resolve(path, root)

        if not p.exists():
            return {"success": False, "error": "Path not found", "code": "NOT_FOUND"}

        try:
            if p.is_dir():
                shutil.rmtree(p)
                return {"success": True, "deleted": str(p), "type": "directory"}
            else:
                p.unlink()
                return {"success": True, "deleted": str(p), "type": "file"}

        except Exception as e:
            return {"success": False, "error": str(e), "code": "DELETE_ERROR"}

    except PermissionError as pe:
        return {"success": False, "error": str(pe), "code": "PATH_OUTSIDE_ROOT"}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "UNKNOWN"}
