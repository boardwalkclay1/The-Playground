# backend/assistant/reasoning_log.py
"""
Optional: store assistant reasoning traces for debugging.
Keep separate from audit logs and ensure redaction of sensitive content.
"""

import json
from pathlib import Path
from .policy import redact_dict

REASONING_DIR = Path("assistant_reasoning")
REASONING_DIR.mkdir(parents=True, exist_ok=True)

def write_trace(session_id: str, trace: dict):
    p = REASONING_DIR / f"{session_id}.jsonl"
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(redact_dict(trace), ensure_ascii=False) + "\n")
    except Exception:
        pass
