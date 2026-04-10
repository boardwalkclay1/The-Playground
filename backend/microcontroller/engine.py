# backend/microcontroller/engine.py
from pathlib import Path
from assistant import AIAgent
import shutil
import os
from typing import Dict

MCU_ROOT = Path("projects/mcu-sandbox")
MCU_ROOT.mkdir(parents=True, exist_ok=True)


def generate_firmware(project_name: str, prompt: str) -> Dict:
    """
    Use the existing AIAgent to generate microcontroller code.
    The assistant should return a structure or plain text that we save as files.
    We pass a clear instruction prefix so the assistant knows to output files.
    """
    agent = AIAgent()
    full_prompt = f"microcontroller-generate\nproject:{project_name}\ninstructions:\n{prompt}\n\nOUTPUT: Provide a JSON mapping of file paths to file contents only."
    result = agent.run(full_prompt, str(MCU_ROOT))
    # Expect result to contain 'files' or 'message' with JSON. Try to parse.
    import json

    files = {}
    if isinstance(result, dict) and result.get("success") and result.get("message"):
        try:
            files = json.loads(result["message"])
        except Exception:
            # fallback: write a single main.ino
            files = {"main.ino": result.get("message", "// no content")}
    else:
        files = {"main.ino": "// assistant did not return structured files"}

    # write files into a sandboxed folder
    target = MCU_ROOT / project_name
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    for path, content in files.items():
        p = target / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    return {"success": True, "project": project_name, "files": list(files.keys())}


def flash_firmware(project_name: str, port: str = None) -> Dict:
    """
    Stub for flashing. If esptool or platformio is available, call them here.
    For safety we provide a stub that reports what would be done.
    """
    target = MCU_ROOT / project_name
    if not target.exists():
        return {"success": False, "error": "Firmware project not found"}

    # locate a firmware binary or .bin file
    bins = list(target.rglob("*.bin"))
    if not bins:
        return {"success": False, "error": "No .bin firmware found to flash"}

    # In a real environment you'd call esptool or platformio here.
    return {"success": True, "message": f"Would flash {bins[0].name} to port {port or 'auto'}"}
