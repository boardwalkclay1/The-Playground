# backend/assistant/routes_ai.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any

from openai_client import fused_chat, generate_image
from assistant.audit_logger import AuditLogger

router = APIRouter(prefix="/ai", tags=["assistant"])

# ---------------------------------------------------------
# SESSION MEMORY
# ---------------------------------------------------------

CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}
audit = AuditLogger()


def get_history(session_id: str) -> List[Dict[str, str]]:
    return CONVERSATIONS.get(session_id, [])


def add_history(session_id: str, role: str, content: str):
    CONVERSATIONS.setdefault(session_id, []).append({"role": role, "content": content})
    CONVERSATIONS[session_id] = CONVERSATIONS[session_id][-40:]  # keep last 40 messages


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------

class AIRequest(BaseModel):
    prompt: str
    session_id: str


class AIImageRequest(AIRequest):
    style: str
    resolution: str


# ---------------------------------------------------------
# LLM HELPERS
# ---------------------------------------------------------

def _run_llm(system: str, session_id: str) -> str:
    messages = [{"role": "system", "content": system}] + get_history(session_id)
    raw = fused_chat(messages)

    if not isinstance(raw, str):
        raise HTTPException(status_code=500, detail="Invalid LLM response")

    return raw


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@router.post("/wiring")
async def ai_wiring(req: AIRequest):
    s = req.session_id
    add_history(s, "user", f"[WIRING] {req.prompt}")

    system = (
        "You are the Boardwalk MCU Wiring Expert.\n"
        "Return ONLY JSON wiring plans, pin mappings, and clear explanations.\n"
        "No markdown. No prose outside JSON."
    )

    text = _run_llm(system, s)

    add_history(s, "assistant", text)
    audit.log("ai_wiring", {"session": s, "prompt": req.prompt, "response": text})

    return {"success": True, "text": text}


@router.post("/code")
async def ai_code(req: AIRequest):
    s = req.session_id
    add_history(s, "user", f"[CODE] {req.prompt}")

    system = (
        "You are the Boardwalk Firmware Generator.\n"
        "Generate deterministic, production-grade MCU firmware.\n"
        "Return ONLY code or JSON. No markdown."
    )

    text = _run_llm(system, s)

    add_history(s, "assistant", text)
    audit.log("ai_code", {"session": s, "prompt": req.prompt, "response": text})

    return {"success": True, "text": text}


@router.post("/image")
async def ai_image(req: AIImageRequest):
    s = req.session_id
    add_history(s, "user", f"[IMAGE] {req.prompt} | style={req.style} | res={req.resolution}")

    try:
        img = generate_image(
            prompt=f"{req.prompt}, style={req.style}",
            size=req.resolution
        )
        url = img.data[0].url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {e}")

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
