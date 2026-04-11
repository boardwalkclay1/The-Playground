# backend/assistant/assistant_api.py
"""
HTTP and WebSocket adapter for assistant actions.
Provides safe endpoints that validate inputs, enforce policy, create sessions, and audit actions.
"""

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import status
from typing import Dict, Any
from pathlib import Path
import asyncio
import json

from .schemas import (
    CreateFileRequest, EditFileRequest, DeleteRequest, MoveRequest,
    RunCommandRequest, AgentRunRequest, PatchRequest, BaseResponse
)
from .session_manager import SessionManager
from .audit_logger import AuditLogger
from .policy import is_command_allowed, requires_approval, max_timeout
from .agent import AIAgent

router = APIRouter()
_sessions = SessionManager()
_agent = AIAgent()

PROJECTS_ROOT = Path("projects")

def _project_path(project_name: str) -> Path:
    p = PROJECTS_ROOT / project_name
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
    return p

@router.post("/assistant/run", response_model=BaseResponse)
async def assistant_run(req: AgentRunRequest):
    project = _project_path(req.project_name)
    sid = _sessions.create_session(user=None, meta={"project": req.project_name})
    audit = AuditLogger(project)
    audit.log("request.received", {"prompt": req.prompt, "session": sid})
    try:
        res = _agent.run(req.prompt, str(project))
        audit.log("request.completed", {"result": res, "session": sid})
        return {"success": bool(res.get("success", True)), "action": res.get("action"), "details": res}
    except Exception as e:
        audit.log("request.error", {"error": str(e), "session": sid})
        raise HTTPException(status_code=500, detail="Assistant error")

@router.post("/assistant/create-file", response_model=BaseResponse)
async def create_file(req: CreateFileRequest):
    project = _project_path(req.path.split("/", 1)[0]) if "/" in req.path else None
    # require project_name in path or use default; prefer explicit project in prompt flow
    # For simplicity, expect client to call assistant_run for project-scoped actions
    raise HTTPException(status_code=400, detail="Use /assistant/run with structured JSON to create files")

@router.post("/assistant/run-command", response_model=BaseResponse)
async def run_command(req: RunCommandRequest, project_name: str):
    project = _project_path(project_name)
    audit = AuditLogger(project)
    if not is_command_allowed(req.command):
        audit.log("command.blocked", {"command": req.command})
        return {"success": False, "error": "Command not allowed by policy"}
    if requires_approval(req.command):
        audit.log("command.requires_approval", {"command": req.command})
        return {"success": False, "error": "Command requires human approval"}
    # delegate to RunTools via agent runner
    res = _agent.runner.run_command(req.command, str(project), timeout=min(req.timeout_seconds or max_timeout(), max_timeout()))
    audit.log("command.executed", {"command": req.command, "result": res})
    return {"success": bool(res.get("success", False)), "details": res}

# WebSocket streaming endpoint for interactive command output
@router.websocket("/assistant/ws/{project_name}")
async def assistant_ws(websocket: WebSocket, project_name: str):
    await websocket.accept()
    project = PROJECTS_ROOT / project_name
    if not project.exists():
        await websocket.send_json({"type": "error", "error": "Project not found"})
        await websocket.close()
        return
    try:
        msg = await websocket.receive_text()
        payload = json.loads(msg)
        command = payload.get("command")
        timeout = int(payload.get("timeout_seconds", max_timeout()))
        if not is_command_allowed(command):
            await websocket.send_json({"type": "error", "error": "Command not allowed by policy"})
            await websocket.close()
            return
        # stream via RunTools.stream_command
        async for out in _agent.runner.stream_command(command, str(project), timeout=timeout):
            await websocket.send_json(out)
        await websocket.close()
    except WebSocketDisconnect:
        return
    except Exception:
        try:
            await websocket.send_json({"type": "error", "error": "Internal error"})
            await websocket.close()
        except Exception:
            pass
