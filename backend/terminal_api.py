# backend/terminal_api.py
"""
Terminal API (Hardened + Policy‑Driven)
--------------------------------------

Features:
- Centralized policy enforcement (policy.py)
- Safe command execution via RunTools
- Structured JSON responses
- WebSocket streaming with timeout + policy checks
- Project‑root safety
- Audit logging
- Redaction
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
import asyncio
import shlex
import json
from typing import Dict, Any, Optional

from assistant.run_tools import RunTools
from assistant.policy import is_command_allowed, requires_approval, max_timeout, redact_dict
from assistant.audit_logger import AuditLogger

router = APIRouter()
PROJECTS_ROOT = Path("projects")
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

audit = AuditLogger(PROJECTS_ROOT)


class TerminalRequest(BaseModel):
    project_name: str
    command: str
    timeout_seconds: Optional[int] = None


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _resolve_project(project_name: str) -> Path:
    p = PROJECTS_ROOT / project_name
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")
    return p


def _safe_split(cmd: str):
    try:
        return shlex.split(cmd)
    except Exception:
        return [cmd]


# ============================================================
# POST /terminal/run
# ============================================================

@router.post("/terminal/run")
async def terminal_run(req: TerminalRequest) -> Dict[str, Any]:
    project_path = _resolve_project(req.project_name)
    cmd = req.command.strip()

    if not cmd:
        raise HTTPException(status_code=400, detail="Empty command")

    # Policy enforcement
    if not is_command_allowed(cmd):
        audit.log("terminal_denied", {"cmd": cmd, "project": req.project_name})
        return {"success": False, "error": "Command not allowed by policy", "code": "DENIED"}

    if requires_approval(cmd):
        audit.log("terminal_requires_approval", {"cmd": cmd, "project": req.project_name})
        return {"success": False, "error": "Command requires approval", "code": "APPROVAL_REQUIRED"}

    timeout = req.timeout_seconds or max_timeout()
    cmd_list = _safe_split(cmd)

    # RunTools execution
    rt = RunTools()
    loop = asyncio.get_event_loop()
    fut = loop.run_in_executor(None, lambda: rt._run(cmd_list, str(project_path)))

    try:
        result = await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        audit.log("terminal_timeout", {"cmd": cmd, "project": req.project_name})
        return {"success": False, "error": "timeout", "code": "TIMEOUT"}

    # Audit
    audit.log("terminal_run", {"cmd": cmd, "project": req.project_name, "result": redact_dict(result)})

    return result


# ============================================================
# WebSocket /terminal/ws/{project_name}
# ============================================================

@router.websocket("/terminal/ws/{project_name}")
async def terminal_ws(websocket: WebSocket, project_name: str):
    await websocket.accept()

    try:
        project_path = _resolve_project(project_name)
    except HTTPException:
        await websocket.send_json({"type": "error", "error": "Project not found"})
        await websocket.close()
        return

    try:
        msg = await websocket.receive_text()
        payload = json.loads(msg)
    except Exception:
        await websocket.send_json({"type": "error", "error": "Invalid JSON"})
        await websocket.close()
        return

    cmd = (payload.get("command") or "").strip()
    timeout = int(payload.get("timeout_seconds") or max_timeout())

    if not cmd:
        await websocket.send_json({"type": "error", "error": "Empty command"})
        await websocket.close()
        return

    # Policy enforcement
    if not is_command_allowed(cmd):
        await websocket.send_json({"type": "error", "error": "Command not allowed"})
        await websocket.close()
        return

    if requires_approval(cmd):
        await websocket.send_json({"type": "error", "error": "Command requires approval"})
        await websocket.close()
        return

    cmd_list = _safe_split(cmd)

    # Start subprocess
    proc = await asyncio.create_subprocess_exec(
        *cmd_list,
        cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    audit.log("terminal_ws_start", {"cmd": cmd, "project": project_name})

    try:
        while True:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await websocket.send_json({"type": "error", "error": "timeout"})
                break

            if not line:
                break

            text = line.decode(errors="replace")
            await websocket.send_json({"type": "stdout", "data": text})

        await proc.wait()
        await websocket.send_json({"type": "exit", "code": proc.returncode})

        audit.log("terminal_ws_exit", {
            "cmd": cmd,
            "project": project_name,
            "exit_code": proc.returncode,
        })

    except WebSocketDisconnect:
        try:
            proc.kill()
        except Exception:
            pass

    except Exception as e:
        audit.log("terminal_ws_error", {"cmd": cmd, "project": project_name, "error": str(e)})
        await websocket.send_json({"type": "error", "error": str(e)})

    finally:
        try:
            await websocket.close()
        except Exception:
            pass
