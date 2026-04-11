# backend/assistant/file_tools.py
"""
Upgraded FileTools

Improvements:
- Uses pathlib for robust path handling and prevents path traversal outside a project root
- Atomic writes via temporary file + rename
- Optional backups with timestamped .bak files
- Convenience helpers: read, write, exists, delete, move, list, read_json, write_json, append
- Returns consistent structured dicts for operations (success, error, path, etc.)
- Simple audit logging to assistant-audit.log in the project root
"""

from pathlib import Path
import tempfile
import shutil
import json
import time
from typing import Any, Dict, List, Optional, Union

AUDIT_FILENAME = "assistant-audit.log"


def _now_ts() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _log_audit(root: Path, entry: Dict[str, Any]) -> None:
    try:
        root.mkdir(parents=True, exist_ok=True)
        log_path = root / AUDIT_FILENAME
        entry = dict(entry)
        entry.setdefault("timestamp", _now_ts())
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # never raise from logging
        pass


def _atomic_write(path: Path, content: Union[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # create temp file in same directory to ensure atomic replace on same filesystem
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with open(fd, "wb") as f:
            if isinstance(content, str):
                f.write(content.encode("utf-8"))
            else:
                f.write(content)
        tmp_path = Path(tmp)
        tmp_path.replace(path)
    finally:
        # ensure no stray temp file
        try:
            if Path(tmp).exists():
                Path(tmp).unlink()
        except Exception:
            pass


def _create_backup(path: Path) -> Optional[str]:
    try:
        if not path.exists():
            return None
        bak = path.with_name(path.name + f".bak.{_now_ts()}")
        shutil.copy2(path, bak)
        return str(bak)
    except Exception:
        return None


def _resolve_root_and_target(root: Union[str, Path], rel_path: Union[str, Path]) -> (Path, Path):
    root_p = Path(root).resolve()
    target = (root_p / str(rel_path)).resolve()
    if not str(target).startswith(str(root_p)):
        raise PermissionError("Path outside project root is not allowed")
    return root_p, target


class FileTools:
    """
    Low-level file operations for the AI assistant.

    Methods return structured dicts:
      {"success": True, "path": "<rel/path>", ...}
      {"success": False, "error": "message"}
    """

    def read(self, root: Union[str, Path], rel_path: Union[str, Path]) -> Dict[str, Any]:
        try:
            root_p, target = _resolve_root_and_target(root, rel_path)
            if not target.exists() or not target.is_file():
                return {"success": False, "error": "File not found", "path": str(rel_path)}
            text = target.read_text(encoding="utf-8", errors="replace")
            _log_audit(root_p, {"action": "read", "path": str(target.relative_to(root_p))})
            return {"success": True, "path": str(target.relative_to(root_p)), "content": text}
        except PermissionError as pe:
            return {"success": False, "error": str(pe)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write(self, root: Union[str, Path], rel_path: Union[str, Path], content: str, overwrite: bool = True, create_backup: bool = True) -> Dict[str, Any]:
        try:
            root_p, target = _resolve_root_and_target(root, rel_path)
            if target.exists() and not overwrite:
                return {"success": False, "error": "File exists and overwrite is False", "path": str(rel_path)}
            backup = None
            if create_backup and target.exists():
                backup = _create_backup(target)
            _atomic_write(target, content)
            _log_audit(root_p, {"action": "write", "path": str(target.relative_to(root_p)), "backup": backup})
            return {"success": True, "path": str(target.relative_to(root_p)), "backup": backup}
        except PermissionError as pe:
            return {"success": False, "error": str(pe)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def exists(self, root: Union[str, Path], rel_path: Union[str, Path]) -> Dict[str, Any]:
        try:
            root_p, target = _resolve_root_and_target(root, rel_path)
            return {"success": True, "exists": target.exists(), "path": str(rel_path)}
        except PermissionError as pe:
            return {"success": False, "error": str(pe)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete(self, root: Union[str, Path], rel_path: Union[str, Path], allow_recursive: bool = False) -> Dict[str, Any]:
        try:
            root_p, target = _resolve_root_and_target(root, rel_path)
            if not target.exists():
                return {"success": False, "error": "Path not found", "path": str(rel_path)}
            if target.is_dir():
                if not allow_recursive:
                    return {"success": False, "error": "Target is a directory; set allow_recursive=True to remove", "path": str(rel_path)}
                shutil.rmtree(target)
                _log_audit(root_p, {"action": "delete_dir", "path": str(target.relative_to(root_p))})
                return {"success": True, "deleted": str(target.relative_to(root_p))}
            else:
                backup = _create_backup(target)
                target.unlink()
                _log_audit(root_p, {"action": "delete_file", "path": str(target.relative_to(root_p)), "backup": backup})
                return {"success": True, "deleted": str(target.relative_to(root_p)), "backup": backup}
        except PermissionError as pe:
            return {"success": False, "error": str(pe)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move(self, root: Union[str, Path], src_rel: Union[str, Path], dst_rel: Union[str, Path], overwrite: bool = False) -> Dict[str, Any]:
        try:
            root_p, src = _resolve_root_and_target(root, src_rel)
            _, dst = _resolve_root_and_target(root, dst_rel)
            if not src.exists():
                return {"success": False, "error": "Source not found", "path": str(src_rel)}
            if dst.exists() and not overwrite:
                return {"success": False, "error": "Destination exists and overwrite is False", "path": str(dst_rel)}
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and overwrite:
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.move(str(src), str(dst))
            _log_audit(root_p, {"action": "move", "from": str(src.relative_to(root_p)), "to": str(dst.relative_to(root_p))})
            return {"success": True, "moved": {"from": str(src.relative_to(root_p)), "to": str(dst.relative_to(root_p))}}
        except PermissionError as pe:
            return {"success": False, "error": str(pe)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list(self, root: Union[str, Path], glob: str = "**/*") -> Dict[str, Any]:
        try:
            root_p = Path(root).resolve()
            if not root_p.exists() or not root_p.is_dir():
                return {"success": False, "error": "Project root not found"}
            items: List[str] = []
            for p in sorted(root_p.glob(glob)):
                if p.is_file():
                    items.append(str(p.relative_to(root_p)))
            _log_audit(root_p, {"action": "list", "count": len(items)})
            return {"success": True, "files": items}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_json(self, root: Union[str, Path], rel_path: Union[str, Path]) -> Dict[str, Any]:
        r = self.read(root, rel_path)
        if not r.get("success"):
            return r
        try:
            data = json.loads(r["content"])
            return {"success": True, "path": r["path"], "json": data}
        except Exception as e:
            return {"success": False, "error": f"JSON parse error: {e}", "path": r.get("path")}

    def write_json(self, root: Union[str, Path], rel_path: Union[str, Path], obj: Any, overwrite: bool = True, create_backup: bool = True) -> Dict[str, Any]:
        try:
            content = json.dumps(obj, indent=2, ensure_ascii=False)
            return self.write(root, rel_path, content, overwrite=overwrite, create_backup=create_backup)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def append(self, root: Union[str, Path], rel_path: Union[str, Path], content: str) -> Dict[str, Any]:
        try:
            root_p, target = _resolve_root_and_target(root, rel_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            # append safely by writing to temp then concatenating
            if not target.exists():
                _atomic_write(target, content)
                _log_audit(root_p, {"action": "append", "path": str(target.relative_to(root_p)), "bytes": len(content)})
                return {"success": True, "path": str(target.relative_to(root_p))}
            # read existing, append, write atomically
            existing = target.read_bytes()
            new_bytes = existing + (content.encode("utf-8"))
            _atomic_write(target, new_bytes)
            _log_audit(root_p, {"action": "append", "path": str(target.relative_to(root_p)), "bytes": len(content)})
            return {"success": True, "path": str(target.relative_to(root_p))}
        except PermissionError as pe:
            return {"success": False, "error": str(pe)}
        except Exception as e:
            return {"success": False, "error": str(e)}
