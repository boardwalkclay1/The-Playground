# backend/assistant/actions.py

import os

class AssistantActions:
    """
    High-level actions the AI can perform.
    """

    def create_file(self, prompt: str, project_path: str):
        parts = prompt.split("create file")
        if len(parts) < 2:
            return {"success": False, "error": "No filename provided."}

        filename = parts[1].strip()
        full_path = os.path.join(project_path, filename)

        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write("")

        return {"success": True, "created": full_path}

    def edit_file(self, prompt: str, project_path: str):
        # Expected format: "edit file path/to/file: new content here"
        if ":" not in prompt:
            return {"success": False, "error": "Missing ':' separator."}

        before, after = prompt.split(":", 1)
        before = before.replace("edit file", "").strip()
        file_path = os.path.join(project_path, before)

        if not os.path.exists(file_path):
            return {"success": False, "error": "File not found."}

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(after.strip())

        return {"success": True, "edited": file_path}

    def delete_file(self, prompt: str, project_path: str):
        filename = prompt.replace("delete", "").strip()
        full_path = os.path.join(project_path, filename)

        if os.path.exists(full_path):
            os.remove(full_path)
            return {"success": True, "deleted": full_path}

        return {"success": False, "error": "File not found."}

    def move_file(self, prompt: str, project_path: str):
        # Format: "move file a to b"
        parts = prompt.replace("move file", "").strip().split(" to ")
        if len(parts) != 2:
            return {"success": False, "error": "Invalid move format."}

        src = os.path.join(project_path, parts[0].strip())
        dst = os.path.join(project_path, parts[1].strip())

        if not os.path.exists(src):
            return {"success": False, "error": "Source file not found."}

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)

        return {"success": True, "moved": {"from": src, "to": dst}}
