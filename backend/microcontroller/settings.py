from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel, validator
import json
import shutil
import time


# ---------------------------------------------------------
# ROOT PATHS
# ---------------------------------------------------------

MCU_ROOT = Path("backend/projects/mcu-sandbox")
MCU_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# SUPPORTED BOARDS
# ---------------------------------------------------------

SUPPORTED_BOARDS = {
    "esp32": {
        "name": "ESP32",
        "default_baud": 115200,
        "flash_mode": "dio",
        "flash_freq": "40m",
    },
    "esp8266": {
        "name": "ESP8266",
        "default_baud": 115200,
        "flash_mode": "dout",
        "flash_freq": "40m",
    },
    "esp32c3": {
        "name": "ESP32-C3",
        "default_baud": 460800,
        "flash_mode": "dio",
        "flash_freq": "80m",
    },
}


# ---------------------------------------------------------
# SETTINGS MODEL
# ---------------------------------------------------------

class MCUSettings(BaseModel):
    board_id: str
    baud_rate: int = 115200
    flash_mode: str = "dio"
    flash_freq: str = "40m"
    upload_port: Optional[str] = None

    @validator("board_id")
    def validate_board(cls, v):
        if v not in SUPPORTED_BOARDS:
            raise ValueError(f"Unsupported board_id: {v}")
        return v

    @validator("flash_mode")
    def validate_flash_mode(cls, v):
        allowed = {"dio", "dout", "qio", "qout"}
        if v not in allowed:
            raise ValueError(f"Invalid flash_mode: {v}")
        return v

    @validator("flash_freq")
    def validate_flash_freq(cls, v):
        allowed = {"20m", "26m", "40m", "80m"}
        if v not in allowed:
            raise ValueError(f"Invalid flash_freq: {v}")
        return v


# ---------------------------------------------------------
# PATH HELPERS
# ---------------------------------------------------------

def _settings_path(project_dir: Path) -> Path:
    return project_dir / "mcu-settings.json"


# ---------------------------------------------------------
# LOAD / SAVE SETTINGS
# ---------------------------------------------------------

def load_settings(project_dir: Path) -> Optional[MCUSettings]:
    """
    Load MCU settings for a project.
    Returns None if no settings exist.
    """
    p = _settings_path(project_dir)

    if not p.exists():
        return None

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return MCUSettings(**data)
    except Exception:
        return None


def save_settings(project_dir: Path, settings: MCUSettings) -> None:
    """
    Save MCU settings atomically.
    """
    p = _settings_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)

    tmp = p.with_suffix(".tmp")
    tmp.write_text(settings.json(indent=2), encoding="utf-8")
    tmp.replace(p)


# ---------------------------------------------------------
# DEFAULT SETTINGS
# ---------------------------------------------------------

def default_settings(board_id: str = "esp32") -> MCUSettings:
    """
    Returns a default MCUSettings object for a given board.
    """
    if board_id not in SUPPORTED_BOARDS:
        raise ValueError(f"Unsupported board_id: {board_id}")

    cfg = SUPPORTED_BOARDS[board_id]

    return MCUSettings(
        board_id=board_id,
        baud_rate=cfg["default_baud"],
        flash_mode=cfg["flash_mode"],
        flash_freq=cfg["flash_freq"],
        upload_port=None,
    )


def ensure_project_settings(project_dir: Path, board_id: str = "esp32") -> MCUSettings:
    """
    Ensures a project has MCU settings.
    If missing, creates defaults.
    """
    existing = load_settings(project_dir)
    if existing:
        return existing

    settings = default_settings(board_id)
    save_settings(project_dir, settings)
    return settings
