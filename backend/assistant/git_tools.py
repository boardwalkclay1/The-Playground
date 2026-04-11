# backend/assistant/git_tools.py
from ..generator.git_clone import clone_repo
from ..generator.repo_ui import build_repo_ui

def assistant_clone_repo(root_dir: str, git_url: str, project_name: str | None = None) -> dict:
    return clone_repo(root_dir, git_url, project_name)

def assistant_build_repo_ui(project_root: str) -> dict:
    return build_repo_ui(project_root)
