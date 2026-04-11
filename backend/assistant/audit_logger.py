# backend/assistant/audit_logger.py
"""
Structured append-only audit logger with optional redaction.
Writes JSON lines to a file inside the project root by default.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from .policy import redact_dict

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

class AuditLogger:
    def __init__(self, project_root: Path, filename: str = "assistant-audit.log"):
        self.project_root = Path(project_root)
        self.log_path = self.project_root / filename
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, payload: Dict[str, Any], actor: Optional[str] = None) -> None:
        entry = {
            "timestamp": _now_iso(),
            "event_type": event_type,
            "actor": actor or "assistant",
            "payload": redact_dict(payload),
        }
        try:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            # never raise from audit logging
            pass
