# backend/assistant/policy.py
"""
Centralized policy for allowed commands, file operations, timeouts, redaction,
and assistant action allowlists.

This module loads assistant-config.json and merges it with defaults.
Environment variables may override specific fields.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List


# ============================================================
# CONFIG PATH
# ============================================================

_CONFIG_PATH = Path(__file__).parent.parent / "assistant-config.json"


# ============================================================
# DEFAULT POLICY
# ============================================================

DEFAULT: Dict[str, Any] = {
    "allowed_command_prefixes": [
        "git ",
        "ls",
        "cat ",
        "python ",
        "python3 ",
        "python -m ",
        "pip ",
        "npm ",
        "node ",
        "echo ",
        "pwd",
        "whoami",
        "curl ",
        "stat ",
        "uvicorn ",
        "pytest ",
        "fastapi ",
    ],

    "allowed_exact": ["pwd", "whoami", "ls"],

    "max_timeout_seconds": 300,
    "allow_unsafe": False,

    "audit_log_path": "assistant-audit.log",

    "require_approval_for": [
        "rm ",
        "sudo ",
        "shutdown",
        "reboot",
        "docker ",
        "kubectl ",
        "truncate ",
        "chmod ",
        "chown ",
        "mkfs ",
        "mount ",
        "umount ",
        "usb_export",
        "apply_patch",
        "delete_file",
        "delete_dir"
    ],

    "redact_keys": [
        "password",
        "secret",
        "token",
        "api_key",
        "auth",
        "bearer",
        "private_key"
    ],

    "assistant_actions_allowed": [
        "create_file",
        "edit_file",
        "delete_file",
        "move_file",
        "list_files",
        "read_file",
        "propose_patch",
        "apply_patch",

        "python_explain",
        "python_generate",
        "python_run",

        "git_clone",

        "analyze_repo",
        "build_repo_ui",

        "usb_list",
        "usb_export"
    ],

    "assistant_actions_require_approval": [
        "delete_file",
        "delete_dir",
        "apply_patch",
        "move_file",
        "usb_export"
    ],
}


# ============================================================
# CONFIG LOADER
# ============================================================

def load_config() -> Dict[str, Any]:
    cfg = DEFAULT.copy()

    # Load assistant-config.json if present
    try:
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update(data)
    except Exception:
        pass  # never break policy loading

    # Environment override for unsafe mode
    if os.environ.get("PLAYGROUND_ALLOW_UNSAFE_COMMANDS", "").lower() in ("1", "true", "yes"):
        cfg["allow_unsafe"] = True

    # Environment override for timeout
    if "ASSISTANT_MAX_TIMEOUT_SECONDS" in os.environ:
        try:
            cfg["max_timeout_seconds"] = int(os.environ["ASSISTANT_MAX_TIMEOUT_SECONDS"])
        except Exception:
            pass

    return cfg


_CONFIG = load_config()


# ============================================================
# COMMAND POLICY
# ============================================================

def is_command_allowed(command: str) -> bool:
    """
    Check if a shell command is allowed by prefix or exact match.
    """
    if not command or not command.strip():
        return False

    if _CONFIG.get("allow_unsafe"):
        return True

    s = command.strip()

    # Exact matches
    if s in _CONFIG.get("allowed_exact", []):
        return True

    # Prefix matches
    for p in _CONFIG.get("allowed_command_prefixes", []):
        if s.startswith(p):
            return True

    return False


def requires_approval(command: str) -> bool:
    """
    Check if a command requires explicit human approval.
    """
    s = command.strip()
    for p in _CONFIG.get("require_approval_for", []):
        if s.startswith(p):
            return True
    return False


# ============================================================
# ASSISTANT ACTION POLICY
# ============================================================

def is_action_allowed(action: str) -> bool:
    """
    Check if an assistant action is allowed.
    """
    allowed = _CONFIG.get("assistant_actions_allowed", [])
    return action in allowed


def action_requires_approval(action: str) -> bool:
    """
    Check if an assistant action requires approval.
    """
    req = _CONFIG.get("assistant_actions_require_approval", [])
    return action in req


# ============================================================
# TIMEOUT POLICY
# ============================================================

def max_timeout() -> int:
    return int(_CONFIG.get("max_timeout_seconds", 300))


# ============================================================
# REDACTION
# ============================================================

def redact_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive keys in a dict for logging/audit.
    """
    out = {}
    redacts = set(k.lower() for k in _CONFIG.get("redact_keys", []))

    for k, v in d.items():
        if k.lower() in redacts:
            out[k] = "<redacted>"
        else:
            out[k] = v

    return out
