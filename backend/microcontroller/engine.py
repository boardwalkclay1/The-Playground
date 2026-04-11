# backend/microcontroller/engine.py
"""
Super-arduino microcontroller engine (ESP-focused)

Features:
- Sandboxed MCU workspace under projects/mcu-sandbox/<project>
- Board picker + serial/flash settings
- Template-based firmware generation (ESP32 examples, custom templates)
- AI-assisted firmware generation (AIAgent)
- Breadboard simulation hook (netlist + rule checks)
- Audit logging for all major actions
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import shutil
import json
import time

from assistant import AIAgent
from assistant.audit_logger import AuditLogger
from assistant.policy import redact_dict

from .templates import (
    list_templates,
    load_template,
    save_template,
)
from .boards import (
    get_board,
    list_boards,
    default_board_id,
)
from .settings import (
    MCUSettings,
    load_settings,
    save_settings,
)
from .breadboard_sim import (
    simulate_circuit,
)
from .examples_esp32 import (
    ensure_esp32_examples_installed,
)

MCU_ROOT = Path("projects/mcu-sandbox")
MCU_ROOT.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def _safe_json_load(text: str) -> Dict[str, str]:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            out: Dict[str, str] = {}
            for k, v in data.items():
                if isinstance(v, str):
                    out[k] = v
                else:
                    out[k] = json.dumps(v, indent=2)
            return out
    except Exception:
        pass
    return {}


def _project_dir(project_name: str) -> Path:
    return MCU_ROOT / project_name


# ---------------------------------------------------------------------------
# Template + board aware firmware generation
# ---------------------------------------------------------------------------

def generate_firmware(
    project_name: str,
    prompt: str,
    template_id: Optional[str] = None,
    board_id: Optional[str] = None,
    merge_strategy: str = "overwrite",  # overwrite | append | hybrid (future)
) -> Dict[str, Any]:
    """
    Generate firmware using:
    - optional template (ESP32 examples or custom)
    - board definition (pins, flash params)
    - AI agent for custom logic

    Result: project folder with files + metadata.
    """
    project_dir = _project_dir(project_name)
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    audit = AuditLogger(MCU_ROOT)

    # Ensure ESP32 example pack is present
    ensure_esp32_examples_installed()

    # Resolve board
    if not board_id:
        board_id = default_board_id()
    board = get_board(board_id)

    # Load settings (baud, flash mode, etc.) or create defaults
    settings = load_settings(project_dir) or MCUSettings(
        board_id=board_id,
        baud_rate=115200,
        flash_mode="dio",
        flash_freq="40m",
        upload_port=None,
    )
    save_settings(project_dir, settings)

    # Start with template files if provided
    base_files: Dict[str, str] = {}
    if template_id:
        tmpl = load_template(template_id)
        base_files.update(tmpl.get("files", {}))

    # Build strict microcontroller prompt
    full_prompt = (
        "microcontroller-generate\n"
        f"project:{project_name}\n"
        f"board:{board_id}\n"
        f"board_meta:{json.dumps(board)}\n"
        f"settings:{settings.json()}\n"
        "instructions:\n"
        f"{prompt}\n\n"
        "CONTEXT:\n"
        "- You are generating firmware for this specific board and settings.\n"
        "- If template files are present, you may extend or modify them.\n"
        "- Respect pin mappings and voltage constraints.\n\n"
        "OUTPUT RULES:\n"
        "- Return ONLY a JSON object mapping file paths to file contents.\n"
        "- No explanations, no markdown, no commentary.\n"
        "- Example: {\"src/main.cpp\": \"<code>\"}\n"
    )

    agent = AIAgent()
    result = agent.run(full_prompt, str(project_dir))

    audit.log("mcu.generate.request", {
        "project": project_name,
        "prompt": prompt,
        "template_id": template_id,
        "board_id": board_id,
        "settings": json.loads(settings.json()),
        "agent_result": redact_dict(result),
    })

    # Extract JSON from agent result
    files: Dict[str, str] = {}
    raw = None
    if isinstance(result, dict):
        raw = (
            result.get("message")
            or result.get("details", {}).get("message")
            or result.get("details", {}).get("output")
        )

    if isinstance(raw, str):
        files = _safe_json_load(raw)

    # Merge with template files
    if not files:
        files = {}
    if merge_strategy == "overwrite":
        merged = {**base_files, **files}
    elif merge_strategy == "append":
        merged = base_files.copy()
        for k, v in files.items():
            if k in merged:
                merged[k] = merged[k] + "\n\n" + v
            else:
                merged[k] = v
    else:  # hybrid placeholder (can be refined later)
        merged = {**base_files, **files}

    if not merged:
        merged = {"main.ino": "// fallback firmware\n"}

    written: List[str] = []
    for rel, content in merged.items():
        safe_rel = rel.lstrip("/").replace("..", "")
        p = project_dir / safe_rel
        _atomic_write(p, content)
        written.append(safe_rel)

    audit.log("mcu.generate.complete", {
        "project": project_name,
        "files": written,
        "board_id": board_id,
        "settings": json.loads(settings.json()),
    })

    return {
        "success": True,
        "project": project_name,
        "files": written,
        "board": board,
        "settings": json.loads(settings.json()),
        "path": str(project_dir),
    }


# ---------------------------------------------------------------------------
# Template management (library)
# ---------------------------------------------------------------------------

def list_firmware_templates() -> Dict[str, Any]:
    return {
        "success": True,
        "templates": list_templates(),
    }


def save_firmware_template(
    template_id: str,
    name: str,
    description: str,
    tags: List[str],
    files: Dict[str, str],
    board_id: Optional[str] = None,
) -> Dict[str, Any]:
    save_template(
        template_id=template_id,
        name=name,
        description=description,
        tags=tags,
        files=files,
        board_id=board_id,
    )
    return {"success": True, "template_id": template_id}


def load_firmware_template(template_id: str) -> Dict[str, Any]:
    tmpl = load_template(template_id)
    if not tmpl:
        return {"success": False, "error": "Template not found"}
    return {"success": True, "template": tmpl}


# ---------------------------------------------------------------------------
# Board + settings
# ---------------------------------------------------------------------------

def list_supported_boards() -> Dict[str, Any]:
    return {"success": True, "boards": list_boards()}


def get_board_settings(project_name: str) -> Dict[str, Any]:
    project_dir = _project_dir(project_name)
    settings = load_settings(project_dir)
    if not settings:
        return {"success": False, "error": "No settings for project"}
    return {"success": True, "settings": json.loads(settings.json())}


def update_board_settings(project_name: str, new_settings: Dict[str, Any]) -> Dict[str, Any]:
    project_dir = _project_dir(project_name)
    current = load_settings(project_dir) or MCUSettings(
        board_id=new_settings.get("board_id") or default_board_id(),
        baud_rate=new_settings.get("baud_rate", 115200),
        flash_mode=new_settings.get("flash_mode", "dio"),
        flash_freq=new_settings.get("flash_freq", "40m"),
        upload_port=new_settings.get("upload_port"),
    )
    updated = MCUSettings(
        board_id=new_settings.get("board_id", current.board_id),
        baud_rate=new_settings.get("baud_rate", current.baud_rate),
        flash_mode=new_settings.get("flash_mode", current.flash_mode),
        flash_freq=new_settings.get("flash_freq", current.flash_freq),
        upload_port=new_settings.get("upload_port", current.upload_port),
    )
    save_settings(project_dir, updated)
    return {"success": True, "settings": json.loads(updated.json())}


# ---------------------------------------------------------------------------
# Flashing (still safe stub, but board/settings aware)
# ---------------------------------------------------------------------------

def flash_firmware(project_name: str) -> Dict[str, Any]:
    project_dir = _project_dir(project_name)
    audit = AuditLogger(MCU_ROOT)

    if not project_dir.exists():
        audit.log("mcu.flash.error", {"project": project_name, "error": "not found"})
        return {"success": False, "error": "Firmware project not found"}

    bins = list(project_dir.rglob("*.bin"))
    if not bins:
        audit.log("mcu.flash.error", {"project": project_name, "error": "no .bin"})
        return {"success": False, "error": "No .bin firmware found to flash"}

    settings = load_settings(project_dir)
    board_id = settings.board_id if settings else default_board_id()
    board = get_board(board_id)

    chosen = bins[0]
    msg = f"Would flash {chosen.name} to port {settings.upload_port or 'auto'} at {settings.baud_rate} baud"

    audit.log("mcu.flash.stub", {
        "project": project_name,
        "bin": chosen.name,
        "board_id": board_id,
        "settings": json.loads(settings.json()) if settings else None,
    })

    return {
        "success": True,
        "message": msg,
        "bin": chosen.name,
        "project": project_name,
        "board": board,
        "settings": json.loads(settings.json()) if settings else None,
    }


# ---------------------------------------------------------------------------
# Breadboard simulation hook
# ---------------------------------------------------------------------------

def simulate_breadboard(project_name: str, netlist: Dict[str, Any]) -> Dict[str, Any]:
    """
    netlist: {
      "board_id": "esp32-devkit-v1",
      "vcc": 5.0,
      "components": [...],
      "connections": [...]
    }
    """
    project_dir = _project_dir(project_name)
    audit = AuditLogger(MCU_ROOT)

    result = simulate_circuit(netlist)
    # Persist last simulation for this project
    sim_path = project_dir / "breadboard-sim.json"
    _atomic_write(sim_path, json.dumps(result, indent=2))

    audit.log("mcu.breadboard.simulated", {
        "project": project_name,
        "netlist": netlist,
        "result": result,
    })

    return {"success": True, "result": result}
