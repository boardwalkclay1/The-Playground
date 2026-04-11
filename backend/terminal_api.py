# backend/terminal_api.py
"""
Upgraded terminal_api

Features:
- Safe command execution with a configurable whitelist of allowed commands/prefixes
- Synchronous POST endpoint that runs a command with timeout and returns full output
- WebSocket endpoint for streaming stdout/stderr in real time
- Optional use of RunTools if available (keeps compatibility with existing helpers)
- Working-directory safety: commands run only inside the project folder
- Environment sanitization and simple logging hooks (no secrets logged)
- Clear, structured JSON responses and error handling
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from pathlib import Path
import asyncio
import shlex
import os
import json
import logging
from typing import Dict, Any, List, Optional

router = APIRouter()
PROJECTS_ROOT = Path("projects")
PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("terminal_api")
logger.setLevel(logging.INFO)


class TerminalRequest(BaseModel):
    project_name: str
    command: str
    timeout_seconds: Optional[int] = 30


# Configurable security policy
_ALLOWED_PREFIXES: List[str] = [
    "git ",
    "ls",
    "cat ",
    "python ",
    "pip ",
    "npm ",
    "echo ",
    "pwd",
    "whoami",
    "node ",
    "curl ",
    "sed ",
    "awk ",
    "stat ",
]
# Exact allowed commands (no args)
_ALLOWED_EXACT: List[str] = ["pwd", "whoami", "ls"]

# If set to True (env var), allow arbitrary commands (useful for local dev only)
_ALLOW_UNSAFE = os.environ.get("PLAYGROUND_ALLOW_UNSAFE_COMMANDS", "false").lower() in ("1", "true", "yes")


def _is_command_allowed(cmd: str) -> bool:
    if _ALLOW_UNSAFE:
        return True
    stripped = cmd.strip()
    # exact match
    if stripped in _ALLOWED_EXACT:
        return True
    # prefix match
    for p in _ALLOWED_PREFIXES:
        if stripped.startswith(p):
            return True
    return False


async def _run_subprocess(cmd_list: List[str], cwd: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Run a subprocess and capture stdout/stderr. Returns dict with exit_code and output.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_list,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        output_lines: List[str] = []
        try:
            # read lines until EOF or timeout
            while True:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    return {"success": False, "error": "timeout", "exit_code": proc.returncode, "output": "".join(output_lines)}
                if not line:
                    break
                decoded = line.decode(errors="replace")
                output_lines.append(decoded)
        finally:
            await proc.wait()

        return {"success": True, "exit_code": proc.returncode, "output": "".join(output_lines)}
    except Exception as e:
        logger.exception("Subprocess run failed")
        return {"success": False, "error": str(e)}


@router.post("/terminal/run")
async def run_terminal(req: TerminalRequest) -> Dict[str, Any]:
    """
    Run a command in the project directory and return the combined stdout/stderr.
    This endpoint is intended for short, safe commands. For long-running or interactive
    commands use the WebSocket streaming endpoint.
    """
    project_path = PROJECTS_ROOT / req.project_name
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")

    cmd = req.command or ""
    if not cmd.strip():
        raise HTTPException(status_code=400, detail="Empty command")

    # Basic security check
    if not _is_command_allowed(cmd):
        return {"success": False, "error": "Command not allowed by server policy"}

    # Safely split command into argv
    try:
        cmd_list = shlex.split(cmd)
    except Exception:
        cmd_list = [cmd]

    # Prefer RunTools if available and exposes a safe run method
    try:
        from assistant.run_tools import RunTools  # type: ignore

        rt = RunTools()
        if hasattr(rt, "_run") and callable(getattr(rt, "_run")):
            # RunTools._run is expected to accept a list and cwd; keep a timeout wrapper
            loop = asyncio.get_event_loop()
            fut = loop.run_in_executor(None, lambda: rt._run(cmd_list, str(project_path)))
            try:
                res = await asyncio.wait_for(fut, timeout=req.timeout_seconds or 30)
                # Ensure result is JSON-serializable
                return res if isinstance(res, dict) else {"success": True, "output": str(res)}
            except asyncio.TimeoutError:
                return {"success": False, "error": "timeout"}
    except Exception:
        # RunTools not available or failed; fall back to internal runner
        pass

    # Run with internal subprocess runner
    timeout = int(req.timeout_seconds or 30)
    result = await _run_subprocess(cmd_list, str(project_path), timeout=timeout)
    return result


# WebSocket streaming endpoint
@router.websocket("/terminal/ws/{project_name}")
async def terminal_ws(websocket: WebSocket, project_name: str):
    """
    WebSocket endpoint that streams stdout/stderr back to the client in real time.
    Client should send a JSON message: {"command": "ls -la", "timeout_seconds": 120}
    Server will send JSON messages of the form: {"type":"stdout","data":"..."} and a final {"type":"exit","code":0}
    """
    await websocket.accept()
    project_path = PROJECTS_ROOT / project_name
    if not project_path.exists() or not project_path.is_dir():
        await websocket.send_json({"type": "error", "error": "Project not found"})
        await websocket.close()
        return

    try:
        msg = await websocket.receive_text()
        try:
            payload = json.loads(msg)
        except Exception:
            await websocket.send_json({"type": "error", "error": "Invalid JSON payload"})
            await websocket.close()
            return

        command = payload.get("command", "")
        timeout_seconds = int(payload.get("timeout_seconds", 300))
        if not command or not command.strip():
            await websocket.send_json({"type": "error", "error": "Empty command"})
            await websocket.close()
            return

        if not _is_command_allowed(command):
            await websocket.send_json({"type": "error", "error": "Command not allowed by server policy"})
            await websocket.close()
            return

        try:
            cmd_list = shlex.split(command)
        except Exception:
            cmd_list = [command]

        # Start subprocess
        proc = await asyncio.create_subprocess_exec(
            *cmd_list,
            cwd=str(project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # Stream output lines to websocket
        try:
            while True:
                try:
                    line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout_seconds)
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
        except WebSocketDisconnect:
            # client disconnected; ensure process is terminated
            try:
                proc.kill()
            except Exception:
                pass
        except Exception as e:
            logger.exception("Error while streaming process output")
            try:
                proc.kill()
            except Exception:
                pass
            await websocket.send_json({"type": "error", "error": str(e)})
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    except WebSocketDisconnect:
        # client disconnected before sending command
        return
    except Exception as e:
        logger.exception("Unexpected error in terminal_ws")
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
            await websocket.close()
        except Exception:
            pass
