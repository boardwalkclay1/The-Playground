# backend/microcontroller/settings.py
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
import json

MCU_ROOT = Path("projects/mcu-sandbox")


class MCUSettings(BaseModel):
    board_id: str
    baud_rate: int = 115200
    flash_mode: str = "dio"
    flash_freq: str = "40m"
    upload_port: Optional[str] = None


def _settings_path(project_dir: Path) -> Path:
    return project_dir / "mcu-settings.json"


def load_settings(project_dir: Path) -> Optional[MCUSettings]:
    p = _settings_path(project_dir)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return MCUSettings(**data)
    except Exception:
        return None


def save_settings(project_dir: Path, settings: MCUSettings) -> None:
    p = _settings_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(settings.json(indent=2), encoding="utf-8")
