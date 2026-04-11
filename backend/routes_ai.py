from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
import uuid

router = APIRouter()

# In-memory conversation store (swap to DB/Redis later)
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}

class AIRequest(BaseModel):
  prompt: str
  session_id: str

class AIImageRequest(AIRequest):
  style: str
  resolution: str

def get_history(session_id: str):
  return CONVERSATIONS.get(session_id, [])

def append_history(session_id: str, role: str, content: str):
  CONVERSATIONS.setdefault(session_id, []).append({"role": role, "content": content})
  # keep last 30 messages
  CONVERSATIONS[session_id] = CONVERSATIONS[session_id][-30:]

@router.post("/ai/wiring")
async def ai_wiring(req: AIRequest):
  history = get_history(req.session_id)
  append_history(req.session_id, "user", req.prompt)

  system = "You are an MCU wiring expert. Output JSON wiring plans and clear explanations."
  messages = [{"role": "system", "content": system}] + history

  # TODO: call your LLM here
  text = "[WIRING RESPONSE HERE]"  # replace with real model call

  append_history(req.session_id, "assistant", text)
  return {"text": text}

@router.post("/ai/code")
async def ai_code(req: AIRequest):
  history = get_history(req.session_id)
  append_history(req.session_id, "user", req.prompt)

  system = "You generate MCU firmware code based on wiring and requirements."
  messages = [{"role": "system", "content": system}] + history

  # TODO: call your LLM here
  text = "[CODE RESPONSE HERE]"

  append_history(req.session_id, "assistant", text)
  return {"text": text}

@router.post("/ai/image")
async def ai_image(req: AIImageRequest):
  history = get_history(req.session_id)
  append_history(req.session_id, "user", f"IMAGE: {req.prompt} | style={req.style} | res={req.resolution}")

  # TODO: call your image model API here (Stable Diffusion / OpenAI / etc.)
  # Example pseudo:
  # image_url = generate_image(req.prompt, style=req.style, resolution=req.resolution)

  image_url = f"/static/generated/{uuid.uuid4()}.png"  # placeholder path

  desc = f"Generated image in style '{req.style}' at {req.resolution}."
  append_history(req.session_id, "assistant", desc)

  return {"image_url": image_url, "description": desc}
