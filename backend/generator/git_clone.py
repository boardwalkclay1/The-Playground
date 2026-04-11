# backend/generator/git_clone.py
import subprocess
from pathlib import Path

def clone_repo(root_dir: str, git_url: str, project_name: str | None = None) -> dict:
    """
    Clone a Git repo into root_dir / project_name.
    If project_name is None, derive from repo name.
    """
    if not project_name:
        project_name = git_url.rstrip("/").split("/")[-1].replace(".git", "")

    target = Path(root_dir) / project_name
    target.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["git", "clone", git_url, str(target)]
    subprocess.check_call(cmd)

    return {
        "ok": True,
        "project_root": str(target),
        "project_name": project_name,
    }
