# backend/assistant/session_manager.py
"""
Simple session manager for assistant interactions.
Generates session IDs and stores lightweight session metadata in-memory and optionally on disk.
"""

import uuid
import json
from pathlib import Path
from typing import Dict, Any, Optional

SESSIONS_DIR = Path("assistant_sessions")
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

class SessionManager:
    def __init__(self, persist: bool = True):
        self.persist = persist
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> str:
        sid = str(uuid.uuid4())
        data = {"id": sid, "user": user, "meta": meta or {}, "created_at": __import__("time").time()}
        self._sessions[sid] = data
        if self.persist:
            p = SESSIONS_DIR / f"{sid}.json"
            try:
                p.write_text(json.dumps(data), encoding="utf-8")
            except Exception:
                pass
        return sid

    def get(self, sid: str) -> Optional[Dict[str, Any]]:
        return self._sessions.get(sid)

    def end_session(self, sid: str) -> None:
        self._sessions.pop(sid, None)
        if self.persist:
            p = SESSIONS_DIR / f"{sid}.json"
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
