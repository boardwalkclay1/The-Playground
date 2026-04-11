# backend/utils/github_ops.py
"""
GitHub Operations (Safe + Token-Aware)
--------------------------------------

Hardened interface for:
- Creating GitHub repositories (real API if token exists)
- Initializing local repo structure
- Writing README / .gitignore
- Making initial commit
- Pushing to GitHub
- Returning structured logs

If no GITHUB_TOKEN is present, operations fall back to safe stubs.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess
import shlex
import json
import os
import time


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run(cmd: str, cwd: Path, timeout: int = 60) -> Dict[str, Any]:
    """
    Safe subprocess wrapper with structured output.
    """
    try:
        proc = subprocess.run(
            shlex.split(cmd),
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": proc.returncode == 0,
            "cmd": cmd,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "cmd": cmd,
            "error": "Executable not found",
            "code": "EXEC_NOT_FOUND",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "cmd": cmd,
            "error": "Command timed out",
            "code": "TIMEOUT",
        }
    except Exception as e:
        return {
            "success": False,
            "cmd": cmd,
            "error": str(e),
            "code": "UNKNOWN_ERROR",
        }


def _github_api_request(token: str, method: str, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    GitHub API call using curl (safe, token-aware).
    """
    cmd = [
        "curl",
        "-s",
        "-X", method,
        "-H", f"Authorization: Bearer {token}",
        "-H", "Accept: application/vnd.github+json",
        "-d", json.dumps(payload),
        url,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        body = proc.stdout.strip()

        try:
            data = json.loads(body)
        except Exception:
            data = {"raw": body}

        return {
            "success": proc.returncode == 0 and isinstance(data, dict),
            "status": proc.returncode,
            "response": data,
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "GitHub API timeout", "code": "TIMEOUT"}

    except Exception as e:
        return {"success": False, "error": str(e), "code": "UNKNOWN"}


# ============================================================
# PUBLIC API
# ============================================================

def create_repo(
    name: str,
    private: bool = True,
    description: str = "",
    auto_init: bool = True,
) -> Dict[str, Any]:
    """
    Create a GitHub repo using the GitHub API if GITHUB_TOKEN is set.
    Otherwise, return a safe stub.
    """
    token = os.getenv("GITHUB_TOKEN")

    # -------------------------
    # FALLBACK STUB (NO TOKEN)
    # -------------------------
    if not token:
        return {
            "success": True,
            "stub": True,
            "message": "GITHUB_TOKEN not set — returning stub repo URL.",
            "repo_url": f"https://github.com/placeholder/{name}",
            "timestamp": _now_iso(),
        }

    # -------------------------
    # REAL GITHUB API CALL
    # -------------------------
    payload = {
        "name": name,
        "private": private,
        "description": description,
        "auto_init": auto_init,
    }

    api = "https://api.github.com/user/repos"
    result = _github_api_request(token, "POST", api, payload)

    if not result.get("success"):
        return {
            "success": False,
            "error": "GitHub API error",
            "details": result,
            "timestamp": _now_iso(),
        }

    repo = result["response"]
    return {
        "success": True,
        "stub": False,
        "repo_url": repo.get("html_url"),
        "ssh_url": repo.get("ssh_url"),
        "clone_url": repo.get("clone_url"),
        "timestamp": _now_iso(),
    }


def init_local_repo(path: str) -> Dict[str, Any]:
    """
    Initialize a local git repo with deterministic steps.
    """
    root = Path(path)
    root.mkdir(parents=True, exist_ok=True)

    steps: List[Dict[str, Any]] = []

    steps.append(_run("git init", root))
    steps.append(_run("git add .", root))
    steps.append(_run('git commit -m "Initial commit"', root))

    return {
        "success": all(s.get("success") for s in steps),
        "steps": steps,
        "timestamp": _now_iso(),
    }


def push_to_github(path: str, remote_url: str) -> Dict[str, Any]:
    """
    Add remote + push initial commit.
    """
    root = Path(path)

    steps: List[Dict[str, Any]] = []

    steps.append(_run(f"git remote add origin {remote_url}", root))
    steps.append(_run("git branch -M main", root))
    steps.append(_run("git push -u origin main", root))

    return {
        "success": all(s.get("success") for s in steps),
        "steps": steps,
        "timestamp": _now_iso(),
    }
