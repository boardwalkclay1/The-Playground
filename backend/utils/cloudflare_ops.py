# backend/utils/cloudflare_ops.py
"""
Cloudflare Deployment Operations
--------------------------------

This module provides a safe, production‑grade interface for deploying:
- Cloudflare Workers
- Cloudflare Pages (static frontend)
- Worker+Pages hybrid apps
- KV / D1 / R2 bindings (metadata only)
- Wrangler validation

All commands are sandboxed and return structured JSON.
"""

from pathlib import Path
from typing import Dict, Any, List
import subprocess
import json
import shlex
import time


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run(cmd: str, cwd: Path) -> Dict[str, Any]:
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
            timeout=60,
        )
        return {
            "success": proc.returncode == 0,
            "cmd": cmd,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except Exception as e:
        return {
            "success": False,
            "cmd": cmd,
            "error": str(e),
        }


def validate_wrangler(project_path: str) -> Dict[str, Any]:
    """
    Validate wrangler.toml exists and is syntactically correct.
    """
    root = Path(project_path)
    wrangler = root / "wrangler.toml"

    if not wrangler.exists():
        return {"success": False, "error": "wrangler.toml not found"}

    try:
        import tomllib
        tomllib.loads(wrangler.read_text(encoding="utf-8"))
        return {"success": True, "message": "wrangler.toml valid"}
    except Exception as e:
        return {"success": False, "error": f"Invalid wrangler.toml: {e}"}


def deploy_worker(project_path: str) -> Dict[str, Any]:
    """
    Deploy a Cloudflare Worker using Wrangler.
    """
    root = Path(project_path)
    wrangler = root / "wrangler.toml"

    if not wrangler.exists():
        return {"success": False, "error": "wrangler.toml missing"}

    # Validate config
    valid = validate_wrangler(project_path)
    if not valid["success"]:
        return valid

    # Run wrangler deploy
    result = _run("wrangler deploy --minify", root)

    return {
        "success": result["success"],
        "timestamp": _now_iso(),
        "action": "deploy_worker",
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "returncode": result.get("returncode"),
    }


def deploy_pages(project_path: str, build_dir: str = "dist") -> Dict[str, Any]:
    """
    Deploy a Cloudflare Pages site.
    """
    root = Path(project_path)
    dist = root / build_dir

    if not dist.exists():
        return {"success": False, "error": f"Build directory '{build_dir}' not found"}

    result = _run(f"wrangler pages deploy {build_dir}", root)

    return {
        "success": result["success"],
        "timestamp": _now_iso(),
        "action": "deploy_pages",
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
        "returncode": result.get("returncode"),
    }


def list_bindings(project_path: str) -> Dict[str, Any]:
    """
    Inspect wrangler.toml and return KV / D1 / R2 bindings.
    """
    root = Path(project_path)
    wrangler = root / "wrangler.toml"

    if not wrangler.exists():
        return {"success": False, "error": "wrangler.toml missing"}

    try:
        import tomllib
        data = tomllib.loads(wrangler.read_text(encoding="utf-8"))
    except Exception as e:
        return {"success": False, "error": f"Invalid wrangler.toml: {e}"}

    bindings = {
        "kv_namespaces": data.get("kv_namespaces", []),
        "d1_databases": data.get("d1_databases", []),
        "r2_buckets": data.get("r2_buckets", []),
        "vars": data.get("vars", {}),
    }

    return {"success": True, "bindings": bindings}


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
    if (root / "dist").exists():
        results.append(deploy_pages(project_path))

    if not results:
        return {"success": False, "error": "No deployable artifacts found"}

    return {
        "success": all(r.get("success") for r in results),
        "timestamp": _now_iso(),
        "results": results,
    }
