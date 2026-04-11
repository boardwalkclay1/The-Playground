# backend/assistant/agent.py
"""
Upgraded AIAgent

Improvements:
- Robust intent detection using keyword and pattern matching
- Safer routing to AssistantActions, FileTools, RunTools, DebugTools
- Support for structured commands (JSON payloads) and natural language
- Full support for Python tools, Git clone, Repo Analyzer, Repo UI, USB tools
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
            pass

    def _debounce(self, key: str) -> bool:
        now = _now_ts()
        last = _RECENT_RUNS.get(key)
        if last and (now - last) < _DEBOUNCE_SECONDS:
            return False
        _RECENT_RUNS[key] = now
        return True

    def _parse_structured(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Detect JSON payloads inside the prompt.
        """
        try:
            m = re.search(r"(\{[\s\S]*\})", prompt)
            if m:
                return json.loads(m.group(1))
        except Exception:
            pass

        try:
            m = re.search(r"command\s*:\s*(\{[\s\S]*\})", prompt, flags=re.IGNORECASE)
            if m:
                return json.loads(m.group(1))
        except Exception:
            pass

        return None

    # =====================================================================
    # MAIN ENTRYPOINT
    # =====================================================================

    def run(self, prompt: str, project_path: str) -> Dict[str, Any]:
        prompt_text = (prompt or "").strip()
        key = f"{project_path}:{prompt_text}"

        if not self._debounce(key):
            return {"success": False, "action": "debounced", "message": "Duplicate request suppressed"}

        self._log_debug("agent.run", {"prompt": prompt_text, "project": project_path})

        # ============================================================
        # 1. STRUCTURED JSON COMMANDS
        # ============================================================
        structured = self._parse_structured(prompt_text)
        if isinstance(structured, dict):
            action = structured.get("action")

            try:
                # ---------------- FILE OPS ----------------
                if action == "create_file":
                    return self.actions.create_file(
                        structured.get("path", ""),
                        project_path,
                        content=structured.get("content", ""),
                        overwrite=structured.get("overwrite", False),
                    )

                if action == "edit_file":
                    if "content" in structured:
                        return self.actions.edit_file(
                            f"edit file {structured.get('path')}: {structured.get('content')}",
                            project_path,
                            create_backup=structured.get("create_backup", True),
                        )
                    if "patch" in structured:
                        return self.actions.apply_patch(
                            structured.get("patch", ""),
                            project_path,
                            create_backup=structured.get("create_backup", True),
                        )

                if action == "delete":
                    return self.actions.delete_file(
                        structured.get("path", ""),
                        project_path,
                        allow_recursive=structured.get("recursive", False),
                    )

                if action == "move":
                    src = structured.get("src")
                    dst = structured.get("dst")
                    if src and dst:
                        return self.actions.move_file(
                            f"move file {src} to {dst}",
                            project_path,
                            overwrite=structured.get("overwrite", False),
                        )

                if action == "list_files":
                    return self.actions.list_files(project_path, glob=structured.get("glob", "**/*"))

                # ---------------- PYTHON ----------------
                if action == "python_explain":
                    return self.actions.python_explain(structured.get("path", ""), project_path)

                if action == "python_generate":
                    return self.actions.python_generate(
                        project_path,
                        structured.get("path", ""),
                        structured.get("description", ""),
                    )

                if action == "python_run":
                    return self.actions.python_run(structured.get("path", ""), project_path)

                # ---------------- GIT ----------------
                if action == "git_clone":
                    return self.actions.git_clone(
                        project_path,
                        structured.get("git_url", ""),
                        structured.get("folder_name", ""),
                    )

                # ---------------- REPO ANALYZER ----------------
                if action == "analyze_repo":
                    return self.actions.analyze_repo(
                        project_path,
                        structured.get("folder", ""),
                    )

                if action == "build_repo_ui":
                    return self.actions.build_repo_ui(
                        project_path,
                        structured.get("folder", ""),
                    )

                # ---------------- USB ----------------
                if action == "usb_list":
                    return self.actions.usb_list()

                if action == "usb_export":
                    return self.actions.usb_export(
                        project_path,
                        structured.get("folder", ""),
                        structured.get("usb_path", ""),
                    )

                # ---------------- RUN COMMAND ----------------
                if action == "run":
                    cmd = structured.get("command")
                    if cmd:
                        if hasattr(self.runner, "run_command"):
                            return self.runner.run_command(cmd, project_path)
                        if hasattr(self.runner, "run"):
                            return self.runner.run(cmd, project_path)

                return {"success": False, "action": "unknown_structured", "message": f"Unknown structured action: {action}"}

            except Exception as e:
                return {"success": False, "action": "structured_error", "error": str(e)}

        # ============================================================
        # 2. NATURAL LANGUAGE INTENT ROUTING
        # ============================================================
        pl = prompt_text.lower()

        # ---------------- FILE OPS ----------------
        if re.search(r"\b(create file|new file)\b", pl):
            return self.actions.create_file(prompt_text, project_path)

        if re.search(r"\b(edit file|edit|change)\b", pl):
            return self.actions.edit_file(prompt_text, project_path)

        if re.search(r"\b(delete|remove)\b", pl):
            return self.actions.delete_file(prompt_text, project_path)

        if re.search(r"\b(move file|move)\b", pl):
            return self.actions.move_file(prompt_text, project_path)

        # ---------------- PYTHON ----------------
        if re.search(r"\b(python explain|explain python)\b", pl):
            m = re.search(r"python explain\s+([^\s]+)", pl)
            if m:
                return self.actions.python_explain(m.group(1), project_path)

        if re.search(r"\b(generate python|new python file)\b", pl):
            m = re.search(r"(?:generate python|new python file)\s+([^\s]+)", pl)
            if m:
                return self.actions.python_generate(project_path, m.group(1), "Generated via natural language")

        if re.search(r"\b(run python|python run)\b", pl):
            m = re.search(r"(?:run python|python run)\s+([^\s]+)", pl)
            if m:
                return self.actions.python_run(m.group(1), project_path)

        # ---------------- GIT ----------------
        if re.search(r"\b(clone repo|git clone)\b", pl):
            m = re.search(r"(?:git clone|clone repo)\s+([^\s]+)", pl)
            if m:
                git_url = m.group(1)
                folder = git_url.rstrip("/").split("/")[-1].replace(".git", "")
                return self.actions.git_clone(project_path, git_url, folder)

        # ---------------- REPO ANALYZER ----------------
        if re.search(r"\b(analyze repo|scan repo|repo info)\b", pl):
            m = re.search(r"(?:analyze repo|scan repo|repo info)\s+([^\s]+)", pl)
            if m:
                return self.actions.analyze_repo(project_path, m.group(1))

        if re.search(r"\b(build repo ui|repo ui)\b", pl):
            m = re.search(r"(?:build repo ui|repo ui)\s+([^\s]+)", pl)
            if m:
                return self.actions.build_repo_ui(project_path, m.group(1))

        # ---------------- USB ----------------
        if re.search(r"\b(list usb|usb list)\b", pl):
            return self.actions.usb_list()

        if re.search(r"\b(export to usb|usb export)\b", pl):
            m = re.search(r"(?:usb export|export to usb)\s+([^\s]+)\s+to\s+([^\s]+)", pl)
            if m:
                folder = m.group(1)
                usb_path = m.group(2)
                return self.actions.usb_export(project_path, folder, usb_path)

        # ---------------- PATCH ----------------
        if re.search(r"\b(patch|diff|apply patch|propose patch)\b", pl):
            patch_match = re.search(r"(?s)(^|\n)(--- .+?)(\n|$)", prompt_text)
            if patch_match:
                return self.actions.propose_patch(patch_match.group(2), project_path)
            return {"success": False, "action": "propose_patch", "message": "No patch found in prompt"}

        # ---------------- RUNNERS ----------------
        if re.search(r"\b(run backend|start backend)\b", pl):
            if hasattr(self.runner, "run_backend"):
                return self.runner.run_backend(project_path)
            if hasattr(self.runner, "run"):
                return self.runner.run("backend", project_path)

        if re.search(r"\b(run frontend|start frontend)\b", pl):
            if hasattr(self.runner, "run_frontend"):
                return self.runner.run_frontend(project_path)
            if hasattr(self.runner, "run"):
                return self.runner.run("frontend", project_path)

        if re.search(r"\b(run worker|start worker)\b", pl):
            if hasattr(self.runner, "run_worker"):
                return self.runner.run_worker(project_path)
            if hasattr(self.runner, "run"):
                return self.runner.run("worker", project_path)

        # ---------------- DEBUG ----------------
        if re.search(r"\b(fix|bug|error|traceback|exception|crash)\b", pl):
            if hasattr(self.debugger, "debug_project"):
                return self.debugger.debug_project(prompt_text, project_path)

        # ---------------- FILE LISTING ----------------
        if re.search(r"\b(list files|show files|ls project)\b", pl):
            return self.actions.list_files(project_path)

        if re.search(r"\b(read file|show file|cat )\b", pl):
            m = re.search(r"(?:read file|show file|cat)\s+([^\n\r]+)", prompt_text, flags=re.IGNORECASE)
            if m:
                return self.actions.read_file(m.group(1).strip(), project_path)

        # ---------------- FALLBACK ----------------
        return {
            "success": True,
            "action": "none",
            "message": "No actionable command detected."
        }
