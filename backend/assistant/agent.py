# backend/assistant/agent.py
"""
Upgraded AIAgent

Improvements:
- Robust intent detection using keyword and pattern matching
- Safer routing to AssistantActions, FileTools, RunTools, DebugTools
- Support for structured commands (JSON payloads) and natural language
- Clear, consistent return payloads with action, success, and details
- Basic rate-limiting / debounce placeholder (to avoid accidental repeated runs)
- Logging hooks via DebugTools when available
"""

from __future__ import annotations
import json
import re
import time
from typing import Any, Dict, Optional

from .actions import AssistantActions
from .file_tools import FileTools
from .run_tools import RunTools
from .debug_tools import DebugTools

# Simple in-memory debounce to avoid repeated identical runs in a short window
_RECENT_RUNS: Dict[str, float] = {}
_DEBOUNCE_SECONDS = 1.0


def _now_ts() -> float:
    return time.time()


class AIAgent:
    """
    Local AI developer engine.
    Decides what action to take based on user prompt.
    """

    def __init__(self):
        self.actions = AssistantActions()
        self.files = FileTools()
        self.runner = RunTools()
        self.debugger = DebugTools()

    def _log_debug(self, *args, **kwargs) -> None:
        try:
            if hasattr(self.debugger, "log"):
                self.debugger.log(*args, **kwargs)
        except Exception:
            # never raise from logging
            pass

    def _debounce(self, key: str) -> bool:
        """
        Return True if the action should be allowed; False if it's a duplicate within debounce window.
        """
        now = _now_ts()
        last = _RECENT_RUNS.get(key)
        if last and (now - last) < _DEBOUNCE_SECONDS:
            return False
        _RECENT_RUNS[key] = now
        return True

    def _parse_structured(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        If the prompt contains a JSON block or a structured command, parse and return it.
        Accepts:
          - JSON object anywhere in the prompt
          - Lines like "command: { ... }"
        """
        # try to find a JSON object in the prompt
        try:
            m = re.search(r"(\{[\s\S]*\})", prompt)
            if m:
                payload = json.loads(m.group(1))
                return payload
        except Exception:
            pass

        # try "command: <json>" style
        try:
            m = re.search(r"command\s*:\s*(\{[\s\S]*\})", prompt, flags=re.IGNORECASE)
            if m:
                payload = json.loads(m.group(1))
                return payload
        except Exception:
            pass

        return None

    def run(self, prompt: str, project_path: str) -> Dict[str, Any]:
        """
        Main entrypoint. Inspects the prompt and routes to the appropriate action.
        Returns a structured dict with at least 'success' and 'action' keys.
        """
        prompt_text = (prompt or "").strip()
        key = f"{project_path}:{prompt_text}"
        if not self._debounce(key):
            return {"success": False, "action": "debounced", "message": "Duplicate request suppressed"}

        self._log_debug("agent.run", {"prompt": prompt_text, "project": project_path})

        # Try structured payload first
        structured = self._parse_structured(prompt_text)
        if isinstance(structured, dict):
            # Expect keys like {"action": "create_file", "path": "...", "content": "..."}
            action = structured.get("action")
            try:
                if action == "create_file":
                    return self.actions.create_file(structured.get("path", ""), project_path, content=structured.get("content", ""), overwrite=structured.get("overwrite", False))
                if action == "edit_file":
                    # support direct content param or unified "patch"
                    if "content" in structured and "path" in structured:
                        # atomic write
                        return self.actions.create_file(structured.get("path", ""), project_path, content=structured.get("content", ""), overwrite=True)
                    if "patch" in structured:
                        return self.actions.apply_patch(structured.get("patch", ""), project_path, create_backup=structured.get("create_backup", True))
                if action == "delete":
                    return self.actions.delete_file(structured.get("path", ""), project_path, allow_recursive=structured.get("recursive", False))
                if action == "move":
                    src = structured.get("src")
                    dst = structured.get("dst")
                    if src and dst:
                        return self.actions.move_file(f"move file {src} to {dst}", project_path, overwrite=structured.get("overwrite", False))
                if action == "list_files":
                    return self.actions.list_files(project_path, glob=structured.get("glob", "**/*"))
                if action == "run":
                    cmd = structured.get("command")
                    if cmd:
                        # delegate to RunTools if it exposes a run method
                        try:
                            if hasattr(self.runner, "run_command"):
                                return self.runner.run_command(cmd, project_path)
                            if hasattr(self.runner, "run"):
                                return self.runner.run(cmd, project_path)
                        except Exception as e:
                            return {"success": False, "error": f"Runner error: {e}"}
                # unknown structured action
                return {"success": False, "action": "unknown_structured", "message": f"Unknown structured action: {action}"}
            except Exception as e:
                return {"success": False, "action": "structured_error", "error": str(e)}

        # Lowercase prompt for keyword matching
        pl = prompt_text.lower()

        # File operations
        if re.search(r"\b(create file|new file)\b", pl):
            try:
                return self.actions.create_file(prompt_text, project_path)
            except Exception as e:
                return {"success": False, "action": "create_file", "error": str(e)}

        if re.search(r"\b(edit file|edit|change)\b", pl):
            try:
                return self.actions.edit_file(prompt_text, project_path)
            except Exception as e:
                return {"success": False, "action": "edit_file", "error": str(e)}

        if re.search(r"\b(delete|remove)\b", pl):
            try:
                return self.actions.delete_file(prompt_text, project_path)
            except Exception as e:
                return {"success": False, "action": "delete_file", "error": str(e)}

        if re.search(r"\b(move file|move)\b", pl):
            try:
                return self.actions.move_file(prompt_text, project_path)
            except Exception as e:
                return {"success": False, "action": "move_file", "error": str(e)}

        # Patch proposals
        if re.search(r"\b(patch|diff|unified diff|apply patch|propose patch)\b", pl):
            # if user provided a patch in the prompt, extract and propose
            patch_match = re.search(r"(?s)(^|\n)(--- .+?)(\n|$)", prompt_text)
            if patch_match:
                patch_text = patch_match.group(2)
                return self.actions.propose_patch(patch_text, project_path)
            return {"success": False, "action": "propose_patch", "message": "No patch found in prompt"}

        # Running commands (delegates to RunTools)
        if re.search(r"\b(run backend|start backend|run server|start server)\b", pl):
            try:
                if hasattr(self.runner, "run_backend"):
                    return self.runner.run_backend(project_path)
                if hasattr(self.runner, "run"):
                    return self.runner.run("backend", project_path)
                return {"success": False, "action": "run_backend", "error": "Runner does not support run_backend"}
            except Exception as e:
                return {"success": False, "action": "run_backend", "error": str(e)}

        if re.search(r"\b(run frontend|start frontend|serve frontend)\b", pl):
            try:
                if hasattr(self.runner, "run_frontend"):
                    return self.runner.run_frontend(project_path)
                if hasattr(self.runner, "run"):
                    return self.runner.run("frontend", project_path)
                return {"success": False, "action": "run_frontend", "error": "Runner does not support run_frontend"}
            except Exception as e:
                return {"success": False, "action": "run_frontend", "error": str(e)}

        if re.search(r"\b(run worker|deploy worker|start worker)\b", pl):
            try:
                if hasattr(self.runner, "run_worker"):
                    return self.runner.run_worker(project_path)
                if hasattr(self.runner, "run"):
                    return self.runner.run("worker", project_path)
                return {"success": False, "action": "run_worker", "error": "Runner does not support run_worker"}
            except Exception as e:
                return {"success": False, "action": "run_worker", "error": str(e)}

        # Microcontroller / firmware generation
        if re.search(r"\b(microcontroller|firmware|generate firmware|arduino|esp32|mcu)\b", pl):
            # delegate to assistant actions if a generate_firmware action exists
            try:
                if hasattr(self.actions, "generate_firmware"):
                    return self.actions.generate_firmware(prompt_text, project_path)
                # fallback: create a stub main.ino
                created = self.actions.create_file("main.ino", project_path, content="// firmware stub\n", overwrite=False)
                return {"success": True, "action": "firmware_stub", "result": created}
            except Exception as e:
                return {"success": False, "action": "firmware", "error": str(e)}

        # Debugging and fixing
        if re.search(r"\b(fix|bug|error|traceback|exception|crash)\b", pl):
            try:
                if hasattr(self.debugger, "debug_project"):
                    return self.debugger.debug_project(prompt_text, project_path)
                return {"success": False, "action": "debug", "message": "Debugger not available"}
            except Exception as e:
                return {"success": False, "action": "debug", "error": str(e)}

        # File listing / reading
        if re.search(r"\b(list files|show files|ls project|what files)\b", pl):
            try:
                return self.actions.list_files(project_path)
            except Exception as e:
                return {"success": False, "action": "list_files", "error": str(e)}

        if re.search(r"\b(read file|show file|cat )\b", pl):
            # attempt to extract filename
            m = re.search(r"(?:read file|show file|cat)\s+([^\n\r]+)", prompt_text, flags=re.IGNORECASE)
            if m:
                filename = m.group(1).strip()
                try:
                    return self.actions.read_file(filename, project_path)
                except Exception as e:
                    return {"success": False, "action": "read_file", "error": str(e)}

        # If nothing matched, return a helpful fallback
        return {
            "success": True,
            "action": "none",
            "message": "No actionable command detected. Try: 'create file <path>', 'edit file <path>: <content>', 'run backend', or provide a structured JSON command."
        }
