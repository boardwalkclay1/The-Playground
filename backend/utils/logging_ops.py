# backend/utils/logging_ops.py
"""
Logging Operations (Structured + Persistent)
--------------------------------------------

This module provides:
- Timestamped structured logs
- Optional project-scoped logs
- Atomic append
- JSONL format (one JSON object per line)
- Console mirroring
"""

from pathlib import Path
from typing import Dict, Any
import json
import time


LOG_ROOT = Path("logs")
LOG_ROOT.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _ensure(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def log(message: str, level: str = "info", project: str | None = None) -> Dict[str, Any]:
    """
    Write a structured log entry to:
    - logs/system.log.jsonl
    - logs/<project>/events.jsonl (if project provided)
    """
    entry = {
        "timestamp": _now_iso(),
        "level": level,
        "message": message,
        "project": project,
    }

    # Console mirror
    print(f"[{entry['timestamp']}] [{level.upper()}] {message}")

    # System log
    system_log = LOG_ROOT / "system.log.jsonl"
    _ensure(system_log)
    with system_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    # Project log
    if project:
        project_log = LOG_ROOT / project / "events.jsonl"
        _ensure(project_log)
        with project_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    return {"success": True, "entry": entry}
