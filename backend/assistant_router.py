# backend/assistant_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, json, subprocess

from openai_client import fused_chat, chat as single_chat

router = APIRouter()

# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------

class AssistantRequest(BaseModel):
    prompt: str
    project_name: Optional[str] = None


class AssistantResponse(BaseModel):
    success: bool
    message: str
    actions: List[Dict[str, Any]] = []
    logs: List[str] = []


# ---------------------------------------------------------
# HISTORY
# ---------------------------------------------------------

def history_path(project_name: Optional[str]) -> str:
    os.makedirs("./projects", exist_ok=True)
    key = project_name or "_global"
    return f"./projects/{key}/.assistant_history.json"


def load_history(project_name: Optional[str]):
    path = history_path(project_name)
    if not os.path.exists(path):
        return []
    try:
        return json.load(open(path, "r", encoding="utf-8"))
    except:
        return []


def save_history(project_name: Optional[str], history):
    path = history_path(project_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(history[-40:], open(path, "w", encoding="utf-8"), indent=2)


# ---------------------------------------------------------
# TOOLS
# ---------------------------------------------------------

def _root(project_name: str):
    base = os.path.abspath(os.path.join("projects", project_name))
    os.makedirs(base, exist_ok=True)
    return base


def tool_read(project_name, path):
    base = _root(project_name)
    full = os.path.normpath(os.path.join(base, path))
    if not full.startswith(base):
        return "ERROR: invalid path"
    try:
        return open(full, "r", encoding="utf-8").read()
    except Exception as e:
        return f"ERROR: {e}"


def tool_write(project_name, path, content):
    base = _root(project_name)
    full = os.path.normpath(os.path.join(base, path))
    if not full.startswith(base):
        return "ERROR: invalid path"
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        open(full, "w", encoding="utf-8").write(content)
        return "OK"
    except Exception as e:
        return f"ERROR: {e}"


def tool_cmd(project_name, command):
    base = _root(project_name)
    try:
        p = subprocess.run(
            command, shell=True, cwd=base,
            capture_output=True, text=True
        )
        return f"EXIT {p.returncode}\nSTDOUT:\n{p.stdout}\nSTDERR:\n{p.stderr}"
    except Exception as e:
        return f"ERROR: {e}"


def tool_ls(project_name, path="."):
    base = _root(project_name)
    target = os.path.normpath(os.path.join(base, path))
    if not target.startswith(base):
        return "ERROR: invalid path"
    tree = []
    for root, dirs, files in os.walk(target):
        tree.append({
            "dir": os.path.relpath(root, base),
            "dirs": dirs,
            "files": files
        })
    return json.dumps(tree, indent=2)


# ---------------------------------------------------------
# MAIN AGENT
# ---------------------------------------------------------

def run_agent(prompt: str, project_name: Optional[str]) -> AssistantResponse:
    logs, actions = [], []

    history = load_history(project_name)
    history.append({"role": "user", "content": prompt})

    # SYSTEM PROMPT
    if project_name:
        system = (
            "You are the Boardwalk Playground Super‑Assistant. "
            "You can chat normally AND operate the project: read/write files, run commands, list files. "
            "Use tools only when needed."
        )
        tools_enabled = True
    else:
        system = (
            "You are the Boardwalk Playground Super‑Assistant. "
            "No project is selected. Chat normally, think deeply, and help freely."
        )
        tools_enabled = False

    messages = [{"role": "system", "content": system}] + history

    # FUSED INTELLIGENCE
    response_text = fused_chat(messages)

    # No tool calls in fused mode (cleaner)
    final = response_text

    history.append({"role": "assistant", "content": final})
    save_history(project_name, history)

    return AssistantResponse(
        success=True,
        message=final,
        actions=actions,
        logs=logs,
    )


# ---------------------------------------------------------
# ROUTE
# ---------------------------------------------------------

@router.post("/assistant/run", response_model=AssistantResponse)
async def assistant_run(req: AssistantRequest):
    return run_agent(req.prompt, req.project_name)
