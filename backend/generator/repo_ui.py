# backend/generator/repo_ui.py
from pathlib import Path
import json

def inspect_repo(project_root: str) -> dict:
    root = Path(project_root)
    files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]

    has_python = any(f.endswith(".py") for f in files)
    has_node = any(f.endswith("package.json") for f in files)
    has_worker = any(f.endswith("worker.js") for f in files)
    has_requirements = any(f.endswith("requirements.txt") for f in files)

    entry_points = []
    for candidate in ("main.py", "server.py", "app.py", "index.js", "worker.js"):
        if any(f.endswith(candidate) for f in files):
            entry_points.append(candidate)

    return {
        "root": project_root,
        "files": files,
        "has_python": has_python,
        "has_node": has_node,
        "has_worker": has_worker,
        "has_requirements": has_requirements,
        "entry_points": entry_points,
    }

def build_repo_ui(project_root: str) -> dict:
    meta = inspect_repo(project_root)

    panels = []

    panels.append({
        "id": "repo-readme",
        "title": "README",
        "type": "markdown-viewer",
        "file": "README.md",
    })

    panels.append({
        "id": "repo-files",
        "title": "Files",
        "type": "file-tree",
        "root": project_root,
    })

    if meta["has_python"]:
        py_entries = [e for e in meta["entry_points"] if e.endswith(".py")]
        panels.append({
            "id": "repo-python-runner",
            "title": "Python Runner",
            "type": "command-runner",
            "commands": [
                {"label": f"Run {e}", "command": f"python3 {e}"} for e in py_entries
            ] or [{"label": "Run main.py", "command": "python3 main.py"}],
        })

    if meta["has_node"]:
        panels.append({
            "id": "repo-node-scripts",
            "title": "Node Scripts",
            "type": "npm-scripts",
            "file": "package.json",
        })

    if meta["has_worker"]:
        panels.append({
            "id": "repo-worker",
            "title": "Cloudflare Worker",
            "type": "worker-runner",
            "entry": "worker.js",
        })

    return {
        "project_root": project_root,
        "meta": meta,
        "panels": panels,
    }
