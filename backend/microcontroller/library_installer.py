# backend/microcontroller/library_installer.py
"""
Simple local library registry for MCU/ESP32 code.

This does NOT touch system Arduino libraries; it tracks libraries
you want the assistant to know about and reference.
"""

from pathlib import Path
from typing import List, Dict, Any
import json

MCU_ROOT = Path("projects/mcu-sandbox")
LIB_ROOT = MCU_ROOT / "libraries"
LIB_ROOT.mkdir(parents=True, exist_ok=True)

REGISTRY_PATH = LIB_ROOT / "registry.json"


def _load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {"libraries": []}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"libraries": []}


def _save_registry(data: Dict[str, Any]) -> None:
    REGISTRY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_libraries() -> List[Dict[str, Any]]:
    return _load_registry().get("libraries", [])


def install_library(name: str, version: str = "local", notes: str = "") -> Dict[str, Any]:
    reg = _load_registry()
    libs = reg.get("libraries", [])
    libs = [l for l in libs if l.get("name") != name]
    libs.append({"name": name, "version": version, "notes": notes})
    reg["libraries"] = libs
    _save_registry(reg)
    return {"success": True, "name": name, "version": version}


def remove_library(name: str) -> Dict[str, Any]:
    reg = _load_registry()
    libs = reg.get("libraries", [])
    new_libs = [l for l in libs if l.get("name") != name]
    if len(new_libs) == len(libs):
        return {"success": False, "error": "Library not found"}
    reg["libraries"] = new_libs
    _save_registry(reg)
    return {"success": True, "name": name}
