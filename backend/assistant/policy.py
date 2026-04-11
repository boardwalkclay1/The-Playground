# backend/assistant/policy.py
"""
Centralized policy for allowed commands, file operations, timeouts, and redaction.
Modify assistant-config.json to change runtime behavior.
"""

import os
from pathlib import Path
from typing import List

# Load overrides from environment or config file if present
_CONFIG_PATH = Path(__file__).parent.parent / "assistant-config.json"

DEFAULT = {
    "allowed_command_prefixes": [
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
    ],
    "allowed_exact": ["pwd", "whoami", "ls"],
    "max_timeout_seconds": 300,
    "allow_unsafe": False,
    "audit_log_path": "assistant-audit.log",
    "require_approval_for": ["rm ", "sudo ", "shutdown", "reboot", "docker ", "kubectl "],
    "redact_keys": ["password", "secret", "token", "api_key"],
}

def load_config() -> dict:
    cfg = DEFAULT.copy()
    try:
        if _CONFIG_PATH.exists():
            import json
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update(data)
    except Exception:
        pass
    # allow env override for unsafe mode
    if os.environ.get("PLAYGROUND_ALLOW_UNSAFE_COMMANDS", "").lower() in ("1", "true", "yes"):
        cfg["allow_unsafe"] = True
    return cfg

_CONFIG = load_config()

def is_command_allowed(command: str) -> bool:
    if not command or not command.strip():
        return False
    if _CONFIG.get("allow_unsafe"):
        return True
    s = command.strip()
    if s in _CONFIG.get("allowed_exact", []):
        return True
    for p in _CONFIG.get("allowed_command_prefixes", []):
        if s.startswith(p):
            return True
    return False

def requires_approval(command: str) -> bool:
    for p in _CONFIG.get("require_approval_for", []):
        if command.strip().startswith(p):
            return True
    return False

def max_timeout() -> int:
    return int(_CONFIG.get("max_timeout_seconds", 300))

def redact_dict(d: dict) -> dict:
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
