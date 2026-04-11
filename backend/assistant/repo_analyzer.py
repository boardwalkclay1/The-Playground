# backend/assistant/repo_analyzer.py
from pathlib import Path

def analyze_repo_structure(project_root: str) -> dict:
    root = Path(project_root)
    files = [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]

    has_python = any(f.endswith(".py") for f in files)
    has_node = any(f.endswith("package.json") for f in files)
    has_worker = any(f.endswith("worker.js") for f in files)
    has_requirements = any(f.endswith("requirements.txt") for f in files)

    return {
        "root": project_root,
        "files": files,
        "has_python": has_python,
        "has_node": has_node,
        "has_worker": has_worker,
        "has_requirements": has_requirements,
    }
