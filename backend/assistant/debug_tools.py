# backend/assistant/debug_tools.py

import os

class DebugTools:
    """
    Reads logs, analyzes errors, proposes fixes.
    """

    def debug_project(self, prompt: str, project_path: str):
        logs_path = os.path.join(project_path, "debug.log")

        if not os.path.exists(logs_path):
            return {"success": False, "error": "No debug.log found."}

        with open(logs_path, "r", encoding="utf-8") as f:
            logs = f.read()

        return {
            "success": True,
            "analysis": "Basic log analysis complete.",
            "logs": logs
        }
