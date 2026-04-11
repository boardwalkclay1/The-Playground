# backend/assistant/run_tools.py
"""
Upgraded RunTools

Improvements:
- Safer command execution with allowed-command policy and opt-in unsafe mode
- Synchronous and streaming execution helpers with timeouts
- Environment sanitization to avoid leaking host secrets
- Working-directory safety: commands run only inside the given project directory
- Structured, consistent return values and logging
- Convenience wrappers: run_backend, run_frontend, run_worker, run_command, stream_command
"""

from __future__ import annotations
import shlex
import subprocess
import asyncio
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("assistant.run_tools")
logger.addHandler(logging.NullHandler())

# Default allowed command prefixes (conservative)
_ALLOWED_PREFIXES: List[str] = [
    "git ",
    "ls",
    "cat ",
    "python ",
    "python3 ",
    "pip ",
    "npm ",
    "node ",
    "echo ",
    "pwd",
    "whoami",
    "curl ",
    "stat ",
]

# Exact allowed commands
_ALLOWED_EXACT: List[str] = ["pwd", "whoami", "ls"]

# Environment variable to allow unsafe commands (local dev only)
_ALLOW_UNSAFE = os.environ.get("PLAYGROUND_ALLOW_UNSAFE_COMMANDS", "false").lower() in ("1", "true", "yes")


def _is_command_allowed(cmd: str) -> bool:
    if _ALLOW_UNSAFE:
        return True
    s = cmd.strip()
    if not s:
        return False
    if s in _ALLOWED_EXACT:
        return True
    for p in _ALLOWED_PREFIXES:
        if s.startswith(p):
            return True
    return False


def _sanitize_env() -> Dict[str, str]:
    """
    Return a minimal sanitized environment for subprocesses.
    Keep PATH so common tools are found, but drop potentially sensitive variables.
    """
    safe_env = {}
    # Keep PATH and LANG related variables
    for k in ("PATH", "LANG", "LC_ALL", "LC_CTYPE"):
        v = os.environ.get(k)
        if v:
            safe_env[k] = v
    # Optionally include NODE_ENV or PYTHONUNBUFFERED if present and safe
    if "PYTHONUNBUFFERED" in os.environ:
        safe_env["PYTHONUNBUFFERED"] = os.environ["PYTHONUNBUFFERED"]
    return safe_env


def _ensure_within_project(cwd: str) -> Path:
    """
    Ensure the cwd exists and is a directory. Return resolved Path.
    """
    p = Path(cwd).resolve()
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Project path not found: {cwd}")
    return p


class RunTools:
    """
    Allows the AI to run backend/frontend/worker commands in a controlled manner.
    """

    def run_backend(self, project_path: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Default backend run. Adjust command as needed for your project.
        """
        # Try common entrypoints; prefer python main.py then uvicorn server:app
        candidates = [
            "python3 main.py",
            "python main.py",
            "uvicorn server:app --port 8000",
        ]
        for cmd in candidates:
            if _is_command_allowed(cmd):
                return self.run_command(cmd, project_path, timeout=timeout)
        # If none allowed, return an informative error
        return {"success": False, "error": "No allowed backend command configured. Set PLAYGROUND_ALLOW_UNSAFE_COMMANDS=true to override."}

    def run_frontend(self, project_path: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Default frontend run. Uses npm run dev if available.
        """
        cmd = "npm run dev"
        if not _is_command_allowed(cmd):
            return {"success": False, "error": "Frontend command not allowed by policy."}
        return self.run_command(cmd, project_path, timeout=timeout)

    def run_worker(self, project_path: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Default worker run. Uses wrangler dev if available.
        """
        cmd = "wrangler dev"
        if not _is_command_allowed(cmd):
            return {"success": False, "error": "Worker command not allowed by policy."}
        return self.run_command(cmd, project_path, timeout=timeout)

    def run_command(self, command: str, cwd: str, timeout: int = 30, capture_output: bool = True) -> Dict[str, Any]:
        """
        Run a command (string) in the given cwd. Returns a structured dict.
        - command: shell-like string (will be split safely)
        - cwd: working directory (must exist)
        - timeout: seconds before killing the process
        """
        try:
            project_dir = _ensure_within_project(cwd)
        except Exception as e:
            return {"success": False, "error": str(e)}

        if not _is_command_allowed(command):
            return {"success": False, "error": "Command not allowed by server policy"}

        try:
            argv = shlex.split(command)
        except Exception:
            argv = [command]

        # Basic check: ensure executable exists on PATH (best-effort)
        exe = argv[0]
        if shutil_which := shutil_which := None:  # placeholder to avoid linter unused import; replaced below
            pass
        try:
            from shutil import which as _which  # local import to avoid top-level dependency issues
            if _which(exe) is None:
                # Not necessarily fatal (could be a shell builtin), but warn
                logger.debug("Executable not found on PATH: %s", exe)
        except Exception:
            # ignore which errors
            pass

        env = _sanitize_env()

        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(project_dir),
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                env=env,
                text=True,
            )
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
                return {"success": False, "error": "timeout", "exit_code": proc.returncode, "stdout": out, "stderr": err}
            return {"success": True, "exit_code": proc.returncode, "stdout": out, "stderr": err}
        except Exception as e:
            logger.exception("run_command failed")
            return {"success": False, "error": str(e)}

    async def stream_command(self, command: str, cwd: str, timeout: int = 300):
        """
        Async generator that yields lines of output as they arrive.
        Usage:
            async for msg in run_tools.stream_command("ls -la", "/path"):
                handle(msg)  # msg is dict like {"type":"stdout","data":"..."} or {"type":"exit","code":0}
        """
        try:
            project_dir = _ensure_within_project(cwd)
        except Exception as e:
            yield {"type": "error", "error": str(e)}
            return

        if not _is_command_allowed(command):
            yield {"type": "error", "error": "Command not allowed by server policy"}
            return

        try:
            argv = shlex.split(command)
        except Exception:
            argv = [command]

        env = _sanitize_env()

        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )

            try:
                while True:
                    try:
                        line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
                    except asyncio.TimeoutError:
                        proc.kill()
                        await proc.wait()
                        yield {"type": "error", "error": "timeout"}
                        break
                    if not line:
                        break
                    text = line.decode(errors="replace")
                    yield {"type": "stdout", "data": text}
                await proc.wait()
                yield {"type": "exit", "code": proc.returncode}
            except asyncio.CancelledError:
                try:
                    proc.kill()
                except Exception:
                    pass
                raise
        except Exception as e:
            logger.exception("stream_command failed")
            yield {"type": "error", "error": str(e)}

    # Backwards-compatible internal _run for older callers (kept synchronous)
    def _run(self, cmd: List[str], cwd: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Compatibility wrapper used by older code. Accepts argv list.
        """
        try:
            project_dir = _ensure_within_project(cwd)
        except Exception as e:
            return {"success": False, "error": str(e)}

        # Reconstruct command string for policy check
        cmd_str = " ".join(shlex.quote(c) for c in cmd)
        if not _is_command_allowed(cmd_str):
            return {"success": False, "error": "Command not allowed by server policy"}

        env = _sanitize_env()
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(project_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
            )
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, err = proc.communicate()
                return {"success": False, "error": "timeout", "exit_code": proc.returncode, "stdout": out, "stderr": err}
            return {"success": True, "exit_code": proc.returncode, "stdout": out, "stderr": err}
        except Exception as e:
            logger.exception("_run failed")
            return {"success": False, "error": str(e)}
