# backend/assistant_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, json, subprocess

from openai_client import chat as openai_chat  # uses your unified OpenAI client

router = APIRouter()

# ---------------------------------------------------------
# CONFIG: MULTI-AI ENGINE
# ---------------------------------------------------------

MODELS = {
    "reasoning": "gpt-4o",
    "coding": "gpt-4o-mini",
    "fast": "gpt-4o-mini",
    "mcu": "gpt-4o-mini",
}

# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------

class AssistantRequest(BaseModel):
    prompt: str
    project_name: Optional[str] = None  # now optional


class AssistantResponse(BaseModel):
    success: bool
    message: str
    actions: List[Dict[str, Any]] = []
    logs: List[str] = []

# ---------------------------------------------------------
# CHAT HISTORY
# ---------------------------------------------------------

def history_path(project_name: Optional[str]) -> str:
    """
    If project_name is provided -> per-project history.
    If not -> global history.
    """
    os.makedirs("./projects", exist_ok=True)
    key = project_name or "_global"
    return f"./projects/{key}/.assistant_history.json"


def load_history(project_name: Optional[str]) -> List[Dict[str, str]]:
    path = history_path(project_name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(project_name: Optional[str], history: List[Dict[str, str]]) -> None:
    path = history_path(project_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history[-40:], f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------
# TOOLS
# ---------------------------------------------------------

def _project_root(project_name: str) -> str:
    base = os.path.abspath(os.path.join("projects", project_name))
    os.makedirs(base, exist_ok=True)
    return base


def tool_read_file(project_name: str, path: str) -> str:
    base = _project_root(project_name)
    full = os.path.normpath(os.path.join(base, path))
    if not full.startswith(base):
        return "ERROR: invalid path"
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"


def tool_write_file(project_name: str, path: str, content: str) -> str:
    base = _project_root(project_name)
    full = os.path.normpath(os.path.join(base, path))
    if not full.startswith(base):
        return "ERROR: invalid path"
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return "OK"
    except Exception as e:
        return f"ERROR: {e}"


def tool_run_command(project_name: str, command: str) -> str:
    base = _project_root(project_name)
    try:
        proc = subprocess.run(
            command,
            shell=True,
            cwd=base,
            capture_output=True,
            text=True,
        )
        return (
            f"EXIT {proc.returncode}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}"
        )
    except Exception as e:
        return f"ERROR: {e}"


def tool_mcu_generate(project_name: str, prompt: str) -> str:
    # hook into your real MCU engine here when ready
    return f"MCU generation requested with prompt: {prompt}"


def tool_list_files(project_name: str, path: str = ".") -> str:
    base = _project_root(project_name)
    target = os.path.normpath(os.path.join(base, path))
    if not target.startswith(base):
        return "ERROR: invalid path"
    tree = []
    for root, dirs, files in os.walk(target):
        rel_root = os.path.relpath(root, base)
        tree.append({"dir": rel_root, "dirs": dirs, "files": files})
    return json.dumps(tree, indent=2)

# ---------------------------------------------------------
# REAL MULTI-AI LLM CALL
# ---------------------------------------------------------

def _build_tool_defs(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tool_defs: List[Dict[str, Any]] = []
    for t in tools:
        name = t["name"]
        desc = t["description"]
        if name == "read_file":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            })
        elif name == "write_file":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            })
        elif name == "run_command":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"],
                    },
                },
            })
        elif name == "mcu_generate":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "mcu_generate",
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": {"prompt": {"type": "string"}},
                        "required": ["prompt"],
                    },
                },
            })
        elif name == "list_files":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": [],
                    },
                },
            })
    return tool_defs


def call_llm(system_prompt: str, history: List[Dict[str, str]], tools: List[Dict[str, Any]], mode: str = "reasoning") -> Dict[str, Any]:
    model = MODELS.get(mode, MODELS["reasoning"])
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    tool_defs = _build_tool_defs(tools)

    resp = openai_chat(
        model=model,
        messages=messages,
        tools=tool_defs if tool_defs else None,
        tool_choice="auto" if tool_defs else "none",
        temperature=0.3,
    )

    msg = resp.choices[0].message

    tool_calls = []
    if getattr(msg, "tool_calls", None):
        for tc in msg.tool_calls:
            tool_calls.append({
                "tool": tc.function.name,
                "args": json.loads(tc.function.arguments or "{}"),
            })

    return {
        "type": "chat",
        "message": msg.content or "",
        "tool_calls": tool_calls,
    }

# ---------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------

def run_agent(prompt: str, project_name: Optional[str]) -> AssistantResponse:
    logs: List[str] = []
    actions: List[Dict[str, Any]] = []

    # history is global if no project_name
    history = load_history(project_name)
    history.append({"role": "user", "content": prompt})

    # tools only available when a project is actually selected
    if project_name:
        tools = [
            {"name": "read_file", "description": "Read a file from the current project"},
            {"name": "write_file", "description": "Write or overwrite a file in the current project"},
            {"name": "run_command", "description": "Run a shell command in the project directory"},
            {"name": "mcu_generate", "description": "Generate microcontroller firmware or code"},
            {"name": "list_files", "description": "List files and folders in the project"},
        ]
        system_prompt = (
            "You are the Boardwalk Playground Studio super-assistant. "
            "You can casually chat, reason deeply, and also fully operate a project when one is selected: "
            "read/write files, run commands, inspect the project tree, and generate MCU code. "
            "Use tools only when they are truly helpful; otherwise just respond conversationally."
        )
    else:
        tools = []
        system_prompt = (
            "You are the Boardwalk Playground Studio super-assistant. "
            "No project is selected. You should behave like a general conversational AI: "
            "chat naturally, reason deeply, and help with anything. "
            "Do NOT mention missing projects or limitations—just respond."
        )

    mode = (
        "coding" if "code" in prompt.lower() or "refactor" in prompt.lower() else
        "mcu" if "microcontroller" in prompt.lower() or "esp32" in prompt.lower() else
        "reasoning"
    )

    # First LLM pass
    llm_result = call_llm(
        system_prompt=system_prompt,
        history=history,
        tools=tools,
        mode=mode,
    )

    # If no project, there should be no tool calls anyway
    if project_name and llm_result.get("tool_calls"):
        for call in llm_result["tool_calls"]:
            t = call["tool"]
            args = call.get("args", {}) or {}

            if t == "read_file":
                path = args.get("path", "")
                result = tool_read_file(project_name, path)
                actions.append({"type": "read_file", "path": path, "result": result})
                logs.append(f"read_file:{path}")
                history.append({"role": "tool", "name": "read_file", "content": result})

            elif t == "write_file":
                path = args.get("path", "")
                content = args.get("content", "")
                result = tool_write_file(project_name, path, content)
                actions.append({"type": "write_file", "path": path, "status": result})
                logs.append(f"write_file:{path}")
                history.append({"role": "tool", "name": "write_file", "content": result})

            elif t == "run_command":
                cmd = args.get("command", "")
                result = tool_run_command(project_name, cmd)
                actions.append({"type": "run_command", "command": cmd, "result": result})
                logs.append(f"run_command:{cmd}")
                history.append({"role": "tool", "name": "run_command", "content": result})

            elif t == "mcu_generate":
                p = args.get("prompt", prompt)
                result = tool_mcu_generate(project_name, p)
                actions.append({"type": "mcu_generate", "prompt": p, "result": result})
                logs.append("mcu_generate")
                history.append({"role": "tool", "name": "mcu_generate", "content": result})

            elif t == "list_files":
                path = args.get("path", ".")
                result = tool_list_files(project_name, path)
                actions.append({"type": "list_files", "path": path, "result": result})
                logs.append(f"list_files:{path}")
                history.append({"role": "tool", "name": "list_files", "content": result})

        # Second LLM pass after tools
        llm_result = call_llm(
            system_prompt=(
                "You have just executed tools on the project. "
                "Explain clearly what you did, what you found, and what you recommend next. "
                "Be concrete and operational, but still conversational."
            ),
            history=history,
            tools=[],
            mode=mode,
        )

    final_message = llm_result.get("message", "No response.")
    history.append({"role": "assistant", "content": final_message})
    save_history(project_name, history)

    return AssistantResponse(
        success=True,
        message=final_message,
        actions=actions,
        logs=logs,
    )

# ---------------------------------------------------------
# ROUTE
# ---------------------------------------------------------

# main.py mounts this router with prefix="/api",
# so this endpoint is available at: POST /api/assistant/run
@router.post("/assistant/run", response_model=AssistantResponse)
async def assistant_run(req: AssistantRequest):
    return run_agent(req.prompt, req.project_name)
