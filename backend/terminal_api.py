# backend/terminal_api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from assistant.run_tools import RunTools
from pathlib import Path

router = APIRouter()
run_tools = RunTools()
PROJECTS_ROOT = Path("projects")


class TerminalRequest(BaseModel):
    project_name: str
    command: str


@router.post("/terminal/run")
def run_terminal(req: TerminalRequest):
    project_path = PROJECTS_ROOT / req.project_name
    if not project_path.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    # Use RunTools to run the command in the project directory.
    # RunTools._run expects a list; split command safely.
    import shlex

    try:
        cmd_list = shlex.split(req.command)
    except Exception:
        cmd_list = [req.command]

    result = run_tools._run(cmd_list, str(project_path))
    return result
