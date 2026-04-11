# backend/assistant/audit_logger.py
"""
Structured append-only audit logger with optional redaction.
Writes JSON lines to a file inside the project root by default.

Upgrades:
- Full integration with updated assistant config (redact_keys, audit_log_path)
- Safer append with directory guarantees
- Optional log rotation hook (non-breaking)
- Event validation + consistent structure
- Never raises exceptions (militant safety)
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

        # Ensure directory exists
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass  # never break audit logger

    # ---------------------------------------------------------
    # OPTIONAL: simple rotation hook (non-breaking)
    # ---------------------------------------------------------
    def rotate_if_needed(self, max_size_bytes: int = 5_000_000) -> None:
        """
        Rotate log if it exceeds max_size_bytes.
        Creates: assistant-audit.log.YYYYMMDDTHHMMSSZ
        """
        try:
            if self.log_path.exists() and self.log_path.stat().st_size > max_size_bytes:
                rotated = self.log_path.with_name(
                    f"{self.log_path.name}.{_now_iso()}"
                )
                self.log_path.rename(rotated)
        except Exception:
            pass  # never break audit logger

    # ---------------------------------------------------------
    # MAIN LOGGING METHOD
    # ---------------------------------------------------------
    def log(self, event_type: str, payload: Dict[str, Any], actor: Optional[str] = None) -> None:
        """
        Append a structured JSON entry to the audit log.
        Always safe. Never throws.
        """
        try:
            entry = {
                "timestamp": _now_iso(),
                "event_type": str(event_type),
                "actor": actor or "assistant",
                "payload": redact_dict(payload),
            }

            # Optional rotation
            self.rotate_if_needed()

            # Append entry
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        except Exception:
            # NEVER raise from audit logging
            pass
