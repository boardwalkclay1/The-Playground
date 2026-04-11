# backend/utils/cloudflare_ops.py
"""
Cloudflare Deployment Operations
--------------------------------

Production‑grade interface for deploying:
- Cloudflare Workers
- Cloudflare Pages (static frontend)
- Worker+Pages hybrid apps
- KV / D1 / R2 / Queues / Vars bindings (metadata only)
- Wrangler validation + version detection

All commands are sandboxed and return structured JSON.
"""

from pathlib import Path
from typing import Dict, Any, List
import subprocess
import json
import shlex
import time


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run(cmd: str, cwd: Path, timeout: int = 60) -> Dict[str, Any]:
    """
    Safe subprocess wrapper.
    Returns stdout/stderr in structured form.
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
            "error": "wrangler CLI not found",
            "code": "WRANGLER_MISSING",
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


def _load_wrangler(project_path: str) -> Dict[str, Any]:
    root = Path(project_path)
    wrangler = root / "wrangler.toml"

    if not wrangler.exists():
        return {"success": False, "error": "wrangler.toml not found", "code": "WRANGLER_MISSING"}

    try:
        import tomllib
        data = tomllib.loads(wrangler.read_text(encoding="utf-8"))
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": f"Invalid wrangler.toml: {e}", "code": "WRANGLER_INVALID"}


# ============================================================
# PUBLIC API
# ============================================================

def wrangler_version() -> Dict[str, Any]:
    """
    Return wrangler version or error.
    """
    result = _run("wrangler --version", Path("."))
    if not result["success"]:
        return result

    return {
        "success": True,
        "version": result["stdout"].strip(),
        "timestamp": _now_iso(),
    }


def validate_wrangler(project_path: str) -> Dict[str, Any]:
    """
    Validate wrangler.toml exists and is syntactically correct.
    """
    return _load_wrangler(project_path)


def list_bindings(project_path: str) -> Dict[str, Any]:
    """
    Inspect wrangler.toml and return KV / D1 / R2 / Queues / Vars bindings.
    """
    loaded = _load_wrangler(project_path)
    if not loaded["success"]:
        return loaded

    data = loaded["data"]

    return {
        "success": True,
        "bindings": {
            "kv_namespaces": data.get("kv_namespaces", []),
            "d1_databases": data.get("d1_databases", []),
            "r2_buckets": data.get("r2_buckets", []),
            "queues": data.get("queues", []),
            "vars": data.get("vars", {}),
        },
        "timestamp": _now_iso(),
    }


def deploy_worker(project_path: str) -> Dict[str, Any]:
    """
    Deploy a Cloudflare Worker using Wrangler.
    """
    root = Path(project_path)

    # Validate wrangler.toml
    valid = validate_wrangler(project_path)
    if not valid["success"]:
        return valid

    # Deploy worker
    result = _run("wrangler deploy --minify", root)

    return {
        "success": result["success"],
        "timestamp": _now_iso(),
        "action": "deploy_worker",
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "returncode": result.get("returncode"),
    }


def deploy_worker_preview(project_path: str) -> Dict[str, Any]:
    """
    Deploy a preview Worker build.
    """
    root = Path(project_path)

    valid = validate_wrangler(project_path)
    if not valid["success"]:
        return valid

    result = _run("wrangler deploy --minify --env preview", root)

    return {
        "success": result["success"],
        "timestamp": _now_iso(),
        "action": "deploy_worker_preview",
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "returncode": result.get("returncode"),
    }


def deploy_pages(project_path: str, build_dir: str = None) -> Dict[str, Any]:
    """
    Deploy a Cloudflare Pages site.
    Auto-detects build directory if not provided.
    """
    root = Path(project_path)

    # Auto-detect build directory
    if build_dir is None:
        for candidate in ["dist", "build", "public", "out"]:
            if (root / candidate).exists():
                build_dir = candidate
                break

    if build_dir is None:
        return {"success": False, "error": "No build directory found", "code": "NO_BUILD_DIR"}

    dist = root / build_dir
    if not dist.exists():
        return {"success": False, "error": f"Build directory '{build_dir}' not found", "code": "NO_BUILD_DIR"}

    result = _run(f"wrangler pages deploy {build_dir}", root)

    return {
        "success": result["success"],
        "timestamp": _now_iso(),
        "action": "deploy_pages",
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "returncode": result.get("returncode"),
    }


def deploy_full_stack(project_path: str) -> Dict[str, Any]:
    """
    Deploy both Worker + Pages if present.
    """
    root = Path(project_path)
    results: List[Dict[str, Any]] = []

    # Worker deploy
    if (root / "wrangler.toml").exists():
        results.append(deploy_worker(project_path))

    # Pages deploy
    for candidate in ["dist", "build", "public", "out"]:
        if (root / candidate).exists():
            results.append(deploy_pages(project_path, candidate))
            break

    if not results:
        return {"success": False, "error": "No deployable artifacts found", "code": "NOTHING_TO_DEPLOY"}

    return {
        "success": all(r.get("success") for r in results),
        "timestamp": _now_iso(),
        "results": results,
    }
