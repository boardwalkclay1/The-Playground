# backend/assistant_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import os, json, subprocess
import openai

router = APIRouter()

# ---------------------------------------------------------
# CONFIG: MULTI‑AI SUPER ENGINE
# ---------------------------------------------------------

openai.api_key = os.getenv("OPENAI_API_KEY")

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
    project_name: str

class AssistantResponse(BaseModel):
    success: bool
    message: str
    actions: List[Dict[str, Any]] = []
    logs: List[str] = []

# ---------------------------------------------------------
# CHAT HISTORY
# ---------------------------------------------------------

def history_path(project_name: str) -> str:
    os.makedirs("./projects", exist_ok=True)
    return f"./projects/{project_name}/.assistant_history.json"

def load_history(project_name: str) -> List[Dict[str, str]]:
    path = history_path(project_name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(project_name: str, history: List[Dict[str, str]]):
    path = history_path(project_name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history[-40:], f, indent=2)

# ---------------------------------------------------------
# TOOLS
# ---------------------------------------------------------

def tool_read_file(project_name: str, path: str) -> str:
    base = f"./projects/{project_name}"
    full = os.path.normpath(os.path.join(base, path))
    if not full.startswith(os.path.abspath(base)):
        return "ERROR: invalid path"
    try:
        with open(full, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"ERROR: {e}"

def tool_write_file(project_name: str, path: str, content: str) -> str:
    base = f"./projects/{project_name}"
    full = os.path.normpath(os.path.join(base, path))
    if not full.startswith(os.path.abspath(base)):
        return "ERROR: invalid path"
    try:
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return "OK"
    except Exception as e:
        return f"ERROR: {e}"

def tool_run_command(project_name: str, command: str) -> str:
    base = f"./projects/{project_name}"
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
    return f"MCU generation requested with prompt: {prompt}"

# ---------------------------------------------------------
# REAL MULTI‑AI LLM CALL
# ---------------------------------------------------------

def call_llm(system_prompt: str, history: List[Dict[str, str]], tools: List[Dict[str, Any]], mode="reasoning"):
    model = MODELS.get(mode, MODELS["reasoning"])

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)

    tool_defs = []
    for t in tools:
        if t["name"] == "read_file":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": t["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"]
                    }
                }
            })
        elif t["name"] == "write_file":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": t["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["path", "content"]
                    }
                }
            })
        elif t["name"] == "run_command":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": t["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"]
                    }
                }
            })
        elif t["name"] == "mcu_generate":
            tool_defs.append({
                "type": "function",
                "function": {
                    "name": "mcu_generate",
                    "description": t["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {"prompt": {"type": "string"}},
                        "required": ["prompt"]
                    }
                }
            })

    resp = openai.chat.completions.create(
        model=model,
        messages=messages,
        tools=tool_defs,
        tool_choice="auto",
    )

    msg = resp.choices[0].message

    tool_calls = []
    if msg.tool_calls:
        for tc in msg.tool_calls:
            tool_calls.append({
                "tool": tc.function.name,
                "args": json.loads(tc.function.arguments or "{}")
            })

    return {
        "type": "chat",
        "message": msg.content or "",
        "tool_calls": tool_calls
    }

# ---------------------------------------------------------
# ORCHESTRATOR
# ---------------------------------------------------------

def run_agent(prompt: str, project_name: str) -> AssistantResponse:
    logs = []
    actions = []

    history = load_history(project_name)
    history.append({"role": "user", "content": prompt})

    tools = [
        {"name": "read_file", "description": "Read a file", "args": ["path"]},
        {"name": "write_file", "description": "Write a file", "args": ["path", "content"]},
        {"name": "run_command", "description": "Run a shell command", "args": ["command"]},
        {"name": "mcu_generate", "description": "Generate MCU firmware", "args": ["prompt"]},
    ]

    mode = (
        "coding" if "code" in prompt.lower() else
        "mcu" if "microcontroller" in prompt.lower() or "esp32" in prompt.lower() else
        "reasoning"
    )

    llm_result = call_llm(
        system_prompt="You are the Boardwalk Playground Studio super‑assistant.",
        history=history,
        tools=tools,
        mode=mode,
    )

    for call in llm_result.get("tool_calls", []):
        t = call["tool"]
        args = call["args"]

        if t == "read_file":
            result = tool_read_file(project_name, args["path"])
            actions.append({"type": "read_file", "path": args["path"], "result": result})
            logs.append(f"read_file:{args['path']}")
            history.append({"role": "tool", "name": "read_file", "content": result})

        elif t == "write_file":
            result = tool_write_file(project_name, args["path"], args["content"])
            actions.append({"type": "write_file", "path": args["path"], "status": result})
            logs.append(f"write_file:{args['path']}")
            history.append({"role": "tool", "name": "write_file", "content": result})

        elif t == "run_command":
            result = tool_run_command(project_name, args["command"])
            actions.append({"type": "run_command", "command": args["command"], "result": result})
            logs.append(f"run_command:{args['command']}")
            history.append({"role": "tool", "name": "run_command", "content": result})

        elif t == "mcu_generate":
            result = tool_mcu_generate(project_name, args["prompt"])
            actions.append({"type": "mcu_generate", "prompt": args["prompt"], "result": result})
            logs.append("mcu_generate")
            history.append({"role": "tool", "name": "mcu_generate", "content": result})

    final_message = llm_result["message"]
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

@router.post("/api/assistant/run", response_model=AssistantResponse)
async def assistant_run(req: AssistantRequest):
    return run_agent(req.prompt, req.project_name)
