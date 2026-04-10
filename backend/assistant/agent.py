# backend/assistant/agent.py

from .actions import AssistantActions
from .file_tools import FileTools
from .run_tools import RunTools
from .debug_tools import DebugTools

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

    def run(self, prompt: str, project_path: str):
        prompt_lower = prompt.lower()

        # File edits
        if "edit" in prompt_lower or "change" in prompt_lower:
            return self.actions.edit_file(prompt, project_path)

        if "create file" in prompt_lower or "new file" in prompt_lower:
            return self.actions.create_file(prompt, project_path)

        if "delete" in prompt_lower:
            return self.actions.delete_file(prompt, project_path)

        if "move" in prompt_lower:
            return self.actions.move_file(prompt, project_path)

        # Running commands
        if "run backend" in prompt_lower:
            return self.runner.run_backend(project_path)

        if "run frontend" in prompt_lower:
            return self.runner.run_frontend(project_path)

        if "run worker" in prompt_lower:
            return self.runner.run_worker(project_path)

        # Debugging
        if "fix" in prompt_lower or "error" in prompt_lower:
            return self.debugger.debug_project(prompt, project_path)

        # Default fallback
        return {
            "success": True,
            "action": "none",
            "message": "Assistant received prompt but no actionable command detected."
        }
