# backend/assistant/hooks.py
"""
Pre/post hooks for assistant actions.
Hook points:
- pre_file_write(root, path, content) -> allow/deny/modify
- pre_run_command(root, command) -> allow/deny/require_approval
- post_action(root, action, result) -> logging/notifications
This module provides default no-op implementations that can be extended per deployment.
"""

from typing import Tuple, Dict, Any

def pre_file_write(root: str, path: str, content: str) -> Tuple[bool, str]:
    """
    Return (allowed, content). If allowed is False, action will be blocked.
    Implementers can modify content (e.g., strip secrets) by returning modified content.
    """
    return True, content

def pre_run_command(root: str, command: str) -> Tuple[bool, str]:
    """
    Return (allowed, command). If allowed is False, action will be blocked.
    """
    return True, command

def post_action(root: str, action: str, result: Dict[str, Any]) -> None:
    """
    Called after an action completes. Use for notifications or additional logging.
    """
    return None
