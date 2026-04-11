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
    RunCommandRequest, AgentRunRequest, PatchRequest, BaseResponse,
    PythonExplainRequest, PythonGenerateRequest, PythonRunRequest,
    GitCloneRequest, AnalyzeRepoRequest, BuildRepoUIRequest,
    USBListRequest, USBExportRequest
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


# ============================================================
# UNIVERSAL ASSISTANT RUN (NATURAL LANGUAGE + STRUCTURED JSON)
# ============================================================

@router.post("/assistant/run", response_model=BaseResponse)
async def assistant_run(req: AgentRunRequest):
    project = _project_path(req.project_name)
    sid = _sessions.create_session(user=None, meta={"project": req.project_name})
    audit = AuditLogger(project)

    audit.log("request.received", {"prompt": req.prompt, "session": sid})

    try:
        res = _agent.run(req.prompt, str(project))
        audit.log("request.completed", {"result": res, "session": sid})
        return {
            "success": bool(res.get("success", True)),
            "action": res.get("action"),
            "details": res
        }
    except Exception as e:
        audit.log("request.error", {"error": str(e), "session": sid})
        raise HTTPException(status_code=500, detail="Assistant error")


# ============================================================
# PYTHON ENDPOINTS
# ============================================================

@router.post("/assistant/python/explain", response_model=BaseResponse)
async def python_explain(req: PythonExplainRequest):
    project = _project_path(req.project_name)
    audit = AuditLogger(project)

    audit.log("python.explain.received", {"path": req.path})

    res = _agent.actions.python_explain(req.path, str(project))
    audit.log("python.explain.completed", {"result": res})

    return {"success": res.get("success", False), "action": "python_explain", "details": res}


@router.post("/assistant/python/generate", response_model=BaseResponse)
async def python_generate(req: PythonGenerateRequest):
    project = _project_path(req.project_name)
    audit = AuditLogger(project)

    audit.log("python.generate.received", {"path": req.path})

    res = _agent.actions.python_generate(str(project), req.path, req.description)
    audit.log("python.generate.completed", {"result": res})

    return {"success": res.get("success", False), "action": "python_generate", "details": res}


@router.post("/assistant/python/run", response_model=BaseResponse)
async def python_run(req: PythonRunRequest):
    project = _project_path(req.project_name)
    audit = AuditLogger(project)

    audit.log("python.run.received", {"path": req.path})

    res = _agent.actions.python_run(req.path, str(project))
    audit.log("python.run.completed", {"result": res})

    return {"success": res.get("success", False), "action": "python_run", "details": res}


# ============================================================
# GIT ENDPOINTS
# ============================================================

@router.post("/assistant/git/clone", response_model=BaseResponse)
async def git_clone(req: GitCloneRequest):
    project = _project_path(req.project_name)
    audit = AuditLogger(project)

    audit.log("git.clone.received", {"repo": req.git_url, "folder": req.folder_name})

    res = _agent.actions.git_clone(str(project), req.git_url, req.folder_name)
    audit.log("git.clone.completed", {"result": res})

    return {"success": res.get("success", False), "action": "git_clone", "details": res}


# ============================================================
# REPO ANALYZER + REPO UI
# ============================================================

@router.post("/assistant/repo/analyze", response_model=BaseResponse)
async def analyze_repo(req: AnalyzeRepoRequest):
    project = _project_path(req.project_name)
    audit = AuditLogger(project)

    audit.log("repo.analyze.received", {"folder": req.folder})

    res = _agent.actions.analyze_repo(str(project), req.folder)
    audit.log("repo.analyze.completed", {"result": res})

    return {"success": res.get("success", False), "action": "analyze_repo", "details": res}


@router.post("/assistant/repo/ui", response_model=BaseResponse)
async def build_repo_ui(req: BuildRepoUIRequest):
    project = _project_path(req.project_name)
    audit = AuditLogger(project)

    audit.log("repo.ui.received", {"folder": req.folder})

    res = _agent.actions.build_repo_ui(str(project), req.folder)
    audit.log("repo.ui.completed", {"result": res})

    return {"success": res.get("success", False), "action": "build_repo_ui", "details": res}


# ============================================================
# USB ENDPOINTS
# ============================================================

@router.post("/assistant/usb/list", response_model=BaseResponse)
async def usb_list(req: USBListRequest):
    # No project needed
    res = _agent.actions.usb_list()
    return {"success": res.get("success", False), "action": "usb_list", "details": res}


@router.post("/assistant/usb/export", response_model=BaseResponse)
async def usb_export(req: USBExportRequest):
    project = _project_path(req.project_name)
    audit = AuditLogger(project)

    audit.log("usb.export.received", {"folder": req.folder, "usb_path": req.usb_path})

    res = _agent.actions.usb_export(str(project), req.folder, req.usb_path)
    audit.log("usb.export.completed", {"result": res})

    return {"success": res.get("success", False), "action": "usb_export", "details": res}


# ============================================================
# COMMAND RUNNER
# ============================================================

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

    res = _agent.runner.run_command(
        req.command,
        str(project),
        timeout=min(req.timeout_seconds or max_timeout(), max_timeout())
    )

    audit.log("command.executed", {"command": req.command, "result": res})
    return {"success": bool(res.get("success", False)), "details": res}


# ============================================================
# WEBSOCKET STREAMING
# ============================================================

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
