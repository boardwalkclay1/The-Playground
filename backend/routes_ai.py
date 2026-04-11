# backend/assistant/routes_ai.py

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
import uuid

from openai_client import chat as openai_chat, generate_image
from assistant.audit_logger import AuditLogger

router = APIRouter()

# In-memory conversation store
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}
audit = AuditLogger()


# ============================================================
# MODELS
# ============================================================

class AIRequest(BaseModel):
    prompt: str
    session_id: str


class AIImageRequest(AIRequest):
    style: str
    resolution: str


# ============================================================
# MEMORY
# ============================================================

def get_history(session_id: str):
    return CONVERSATIONS.get(session_id, [])


def add_history(session_id: str, role: str, content: str):
    CONVERSATIONS.setdefault(session_id, []).append({"role": role, "content": content})
    CONVERSATIONS[session_id] = CONVERSATIONS[session_id][-30:]


# ============================================================
# LLM CALLS
# ============================================================

def wiring_llm(messages):
    resp = openai_chat(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )
    return resp.choices[0].message.content


def code_llm(messages):
    resp = openai_chat(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2
    )
    return resp.choices[0].message.content


def image_llm(prompt, style, resolution):
    img = generate_image(
        prompt=f"{prompt}, style={style}",
        size=resolution
    )
    return img.data[0].url


# ============================================================
# ROUTES
# ============================================================

@router.post("/ai/wiring")
async def ai_wiring(req: AIRequest):
    s = req.session_id
    add_history(s, "user", f"[WIRING] {req.prompt}")

    system = (
        "You are Boardwalk MCU Wiring Expert. "
        "Output JSON wiring plans, pin mappings, diagrams, and clear explanations."
    )

    messages = [{"role": "system", "content": system}] + get_history(s)
    text = wiring_llm(messages)

    add_history(s, "assistant", text)
    audit.log("ai_wiring", {"session": s, "prompt": req.prompt, "response": text})

    return {"success": True, "text": text}


@router.post("/ai/code")
async def ai_code(req: AIRequest):
    s = req.session_id
    add_history(s, "user", f"[CODE] {req.prompt}")

    system = (
        "You are Boardwalk Firmware Generator. "
        "Generate deterministic, production-grade MCU firmware."
    )

    messages = [{"role": "system", "content": system}] + get_history(s)
    text = code_llm(messages)

    add_history(s, "assistant", text)
    audit.log("ai_code", {"session": s, "prompt": req.prompt, "response": text})

    return {"success": True, "text": text}


@router.post("/ai/image")
async def ai_image(req: AIImageRequest):
    s = req.session_id
    add_history(s, "user", f"[IMAGE] {req.prompt} | style={req.style} | res={req.resolution}")

    url = image_llm(req.prompt, req.style, req.resolution)
    desc = f"Generated image in style '{req.style}' at {req.resolution}."

    add_history(s, "assistant", desc)
    audit.log("ai_image", {
        "session": s,
        "prompt": req.prompt,
        "style": req.style,
        "resolution": req.resolution,
        "image_url": url,
    })

    return {"success": True, "image_url": url, "description": desc}
