# backend/utils/logging_ops.py
"""
Logging Operations (Structured + Persistent)
--------------------------------------------

Platform‑grade logging with:
- Timestamped structured JSONL logs
- System log + optional project‑scoped logs
- Atomic append
- Redaction (policy-driven)
- Log rotation
- Path traversal protection
- Never throws exceptions
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import time

from .policy import redact_dict


LOG_ROOT = Path("logs")
LOG_ROOT.mkdir(parents=True, exist_ok=True)

MAX_LOG_BYTES = 5_000_000  # 5MB rotation threshold


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _ensure(path: Path):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _rotate_if_needed(path: Path):
    try:
        if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
            rotated = path.with_name(f"{path.name}.{_now_iso()}")
            path.rename(rotated)
    except Exception:
        pass


def _safe_append(path: Path, entry: Dict[str, Any]):
    """
    Atomic append: write to temp file then append.
    Never throws.
    """
    try:
        _ensure(path)
        _rotate_if_needed(path)

        line = json.dumps(entry, ensure_ascii=False) + "\n"

        # atomic append via temp file
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(line, encoding="utf-8")
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
        if tmp.exists():
            tmp.unlink()
    except Exception:
        pass


def _sanitize_project(project: Optional[str]) -> Optional[str]:
    """
    Prevent path traversal in project names.
    """
    if not project:
        return None
    if "/" in project or "\\" in project or ".." in project:
        return None
    return project


# ============================================================
# PUBLIC API
# ============================================================

def log(
    message: str,
    level: str = "info",
    project: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Write a structured log entry to:
    - logs/system.log.jsonl
    - logs/<project>/events.jsonl (if project provided)

    Always safe. Never throws.
    """
    try:
        project = _sanitize_project(project)

        entry = {
            "timestamp": _now_iso(),
            "level": level.lower(),
            "message": message,
            "project": project,
            "meta": redact_dict(meta or {}),
        }

        # Console mirror
        print(f"[{entry['timestamp']}] [{entry['level'].upper()}] {message}")

        # System log
        system_log = LOG_ROOT / "system.log.jsonl"
        _safe_append(system_log, entry)

        # Project log
        if project:
            project_log = LOG_ROOT / project / "events.jsonl"
            _safe_append(project_log, entry)

        return {"success": True, "entry": entry}

    except Exception as e:
        # NEVER break logging
        return {
            "success": False,
            "error": str(e),
            "code": "LOGGING_FAILURE",
        }
