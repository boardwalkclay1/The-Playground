# backend/assistant_router.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
import os, json, subprocess

router = APIRouter()

# ---------- MODELS ----------

class AssistantRequest(BaseModel):
  prompt: str
  project_name: str

class AssistantResponse(BaseModel):
  success: bool
  message: str
  actions: List[Dict[str, Any]] = []
  logs: List[str] = []

# ---------- CHAT HISTORY PER PROJECT ----------

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
  except Exception:
    return []

def save_history(project_name: str, history: List[Dict[str, str]]) -> None:
  path = history_path(project_name)
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "w", encoding="utf-8") as f:
    json.dump(history[-40:], f, ensure_ascii=False, indent=2)  # keep last 40 turns

# ---------- TOOLS ----------

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
  # hook into your existing MCU engine
  # from .mcu import generate_firmware
  # res = generate_firmware(project_name=project_name, prompt=prompt)
  # return json.dumps(res, indent=2)
  return "MCU TOOL STUB: wire this to your real MCU generator."

# ---------- LLM CALL (PLUG YOUR PROVIDER HERE) ----------

def call_llm(system_prompt: str, history: List[Dict[str, str]], tools: List[Dict[str, Any]]) -> Dict[str, Any]:
  """
  You plug your real LLM here (OpenAI, local, etc.).
  It should return something like:
  {
    "type": "chat",
    "message": "human-facing answer",
    "tool_calls": [
      {"tool": "read_file", "args": {"path": "src/main.py"}},
      {"tool": "write_file", "args": {"path": "src/main.py", "content": "..."}}
    ]
  }
  For now this is a stub that just chats.
  """
  last_user = history[-1]["content"] if history else ""
  return {
    "type": "chat",
    "message": f"(stub) I see: {last_user}",
    "tool_calls": []
  }

# ---------- ORCHESTRATOR ----------

def run_agent(prompt: str, project_name: str) -> AssistantResponse:
  logs: List[str] = []
  actions: List[Dict[str, Any]] = []

  # load history and append user
  history = load_history(project_name)
  history.append({"role": "user", "content": prompt})

  # define tools for the LLM (names + args schema)
  tools = [
    {"name": "read_file", "description": "Read a file from the project", "args": ["path"]},
    {"name": "write_file", "description": "Write a file in the project", "args": ["path", "content"]},
    {"name": "run_command", "description": "Run a shell command in the project directory", "args": ["command"]},
    {"name": "mcu_generate", "description": "Generate microcontroller firmware", "args": ["prompt"]},
  ]

  # call LLM
  llm_result = call_llm(
    system_prompt=(
      "You are the Boardwalk Playground Studio assistant. "
      "You can read/write files, run commands, and generate microcontroller code. "
      "Always explain what you did in plain language."
    ),
    history=history,
    tools=tools,
  )

  # handle tool calls (loop until no more tools or you decide to stop)
  for call in llm_result.get("tool_calls", []):
    t = call.get("tool")
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

  # final assistant message
  message = llm_result.get("message", "No response.")

  # append assistant to history and save
  history.append({"role": "assistant", "content": message})
  save_history(project_name, history)

  return AssistantResponse(
    success=True,
    message=message,
    actions=actions,
    logs=logs,
  )

# ---------- ROUTE ----------

@router.post("/api/assistant/run", response_model=AssistantResponse)
async def assistant_run(req: AssistantRequest):
  return run_agent(req.prompt, req.project_name)
