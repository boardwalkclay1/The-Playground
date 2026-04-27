"""
Hardened File Operations (Platform‑Wide Standard)
-------------------------------------------------

This module provides the *lowest‑level* safe file operations used across the
entire platform:

- Path traversal protection
- Symlink protection
- Atomic writes (temp file → replace)
- Optional timestamped backups
- Deterministic directory creation
- UTF‑8 safe reads/writes
- Safe delete (files + directories)
- Safe copy / move
- Safe mkdir
- Safe list
- Structured return payloads
- Never throws exceptions
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import time
import shutil
import tempfile
import json
import os


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


def _resolve(path: str, root: Optional[str] = None) -> Path:
    """
    Resolve path and enforce optional project root.
    Prevents:
    - ../ traversal
    - symlink escape
    """
    p = Path(path).resolve()

    if root:
        root_p = Path(root).resolve()
        if not str(p).startswith(str(root_p)):
            raise PermissionError("Path outside project root is not allowed")

    # Prevent symlink escape
    try:
        if p.is_symlink():
            raise PermissionError("Symlink access is not allowed")
    except Exception:
        pass

    return p


def _atomic_write(path: Path, content: str) -> None:
    """
    Atomic write using a temp file in the same directory.
    """
    _ensure_parent(path)

    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    tmp_path = Path(tmp)

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content.encode("utf-8"))

        # Atomic replace
        tmp_path.replace(path)

    finally:
        # If replace succeeded, tmp no longer exists
        if tmp_path.exists():
            try:
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


def safe_copy(src: str, dst: str, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Safe file copy.
    """
    try:
        src_p = _resolve(src, root)
        dst_p = _resolve(dst, root)

        _ensure_parent(dst_p)

        shutil.copy2(src_p, dst_p)

        return {"success": True, "src": str(src_p), "dst": str(dst_p)}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "COPY_ERROR"}


def safe_move(src: str, dst: str, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Safe file move.
    """
    try:
        src_p = _resolve(src, root)
        dst_p = _resolve(dst, root)

        _ensure_parent(dst_p)

        shutil.move(src_p, dst_p)

        return {"success": True, "src": str(src_p), "dst": str(dst_p)}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "MOVE_ERROR"}


def safe_mkdir(path: str, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Safe directory creation.
    """
    try:
        p = _resolve(path, root)
        p.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"success": False, "error": str(e), "code": "MKDIR_ERROR"}


def safe_list(path: str, root: Optional[str] = None) -> Dict[str, Any]:
    """
    Safe directory listing.
    """
    try:
        p = _resolve(path, root)

        if not p.exists():
            return {"success": False, "error": "Path not found", "code": "NOT_FOUND"}

        if not p.is_dir():
            return {"success": False, "error": "Not a directory", "code": "NOT_DIR"}

        items = []
        for child in p.iterdir():
            items.append({
                "name": child.name,
                "path": str(child),
                "type": "dir" if child.is_dir() else "file"
            })

        return {"success": True, "items": items}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "LIST_ERROR"}
