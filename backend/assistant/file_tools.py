# backend/assistant/file_tools.py

import os

class FileTools:
    """
    Low-level file operations for the AI assistant.
    """

    def read(self, path: str):
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write(self, path: str, content: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    def exists(self, path: str):
        return os.path.exists(path)
