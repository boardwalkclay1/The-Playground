# backend/assistant/ai_panel_api.py

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
# MEMORY HELPERS
# ============================================================

def get_history(session_id: str):
    return CONVERSATIONS.get(session_id, [])


def append_history(session_id: str, role: str, content: str):
    CONVERSATIONS.setdefault(session_id, []).append({"role": role, "content": content})
    CONVERSATIONS[session_id] = CONVERSATIONS[session_id][-30:]


# ============================================================
# REAL LLM CALLS
# ============================================================

def call_wiring_llm(messages: List[Dict[str, str]]) -> str:
    resp = openai_chat(
        model="gpt-4o",
        messages=messages,
        temperature=0.2
    )
    return resp.choices[0].message.content


def call_code_llm(messages: List[Dict[str, str]]) -> str:
    resp = openai_chat(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2
    )
    return resp.choices[0].message.content


def call_image_engine(prompt: str, style: str, resolution: str) -> str:
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
    session = req.session_id
    append_history(session, "user", f"[WIRING] {req.prompt}")

    system = (
        "You are Boardwalk MCU Wiring Expert. "
        "Output JSON wiring plans, pin mappings, diagrams, and clear explanations."
    )

    messages = [{"role": "system", "content": system}] + get_history(session)
    text = call_wiring_llm(messages)

    append_history(session, "assistant", text)
    audit.log("ai_wiring", {"session": session, "prompt": req.prompt, "response": text})

    return {"success": True, "text": text}


@router.post("/ai/code")
async def ai_code(req: AIRequest):
    session = req.session_id
    append_history(session, "user", f"[CODE] {req.prompt}")

    system = (
        "You are Boardwalk Firmware Generator. "
        "Generate deterministic, production-grade MCU firmware."
    )

    messages = [{"role": "system", "content": system}] + get_history(session)
    text = call_code_llm(messages)

    append_history(session, "assistant", text)
    audit.log("ai_code", {"session": session, "prompt": req.prompt, "response": text})

    return {"success": True, "text": text}


@router.post("/ai/image")
async def ai_image(req: AIImageRequest):
    session = req.session_id
    append_history(
        session,
        "user",
        f"[IMAGE] {req.prompt} | style={req.style} | res={req.resolution}",
    )

    image_url = call_image_engine(req.prompt, req.style, req.resolution)
    desc = f"Generated image in style '{req.style}' at {req.resolution}."

    append_history(session, "assistant", desc)
    audit.log("ai_image", {
        "session": session,
        "prompt": req.prompt,
        "style": req.style,
        "resolution": req.resolution,
        "image_url": image_url,
    })

    return {"success": True, "image_url": image_url, "description": desc}
