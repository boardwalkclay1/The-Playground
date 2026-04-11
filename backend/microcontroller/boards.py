# backend/microcontroller/boards.py
from pathlib import Path
from typing import Dict, Any, List
import json

MCU_ROOT = Path("projects/mcu-sandbox")
DATA_ROOT = MCU_ROOT / "data"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

BOARDS_PATH = DATA_ROOT / "boards_index.json"


_DEFAULT_BOARDS = {
    "boards": [
        {
            "id": "esp32-devkit-v1",
            "name": "ESP32 DevKit V1",
            "vendor": "Espressif",
            "voltage": 3.3,
            "max_current_ma": 500,
            "flash_mode": "dio",
            "flash_freq": "40m",
            "default_baud": 115200,
            "pins": {
                "3V3": "3.3V output",
                "GND": "Ground",
                "GPIO2": "LED / IO",
                "GPIO4": "IO",
                "GPIO5": "IO",
                "GPIO12": "IO",
                "GPIO13": "IO",
                "GPIO14": "IO",
                "GPIO15": "IO",
                "GPIO16": "IO",
                "GPIO17": "IO",
                "GPIO18": "SCK",
                "GPIO19": "MISO",
                "GPIO21": "SDA",
                "GPIO22": "SCL",
                "GPIO23": "MOSI",
                "GPIO25": "DAC1",
                "GPIO26": "DAC2",
                "GPIO32": "ADC",
                "GPIO33": "ADC",
                "GPIO34": "ADC input only",
                "GPIO35": "ADC input only",
            },
        }
    ]
}


def _ensure_boards_file():
    if not BOARDS_PATH.exists():
        BOARDS_PATH.write_text(json.dumps(_DEFAULT_BOARDS, indent=2), encoding="utf-8")


def _load_boards() -> Dict[str, Any]:
    _ensure_boards_file()
    try:
        return json.loads(BOARDS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _DEFAULT_BOARDS


def list_boards() -> List[Dict[str, Any]]:
    return _load_boards().get("boards", [])


def get_board(board_id: str) -> Dict[str, Any]:
    boards = list_boards()
    for b in boards:
        if b.get("id") == board_id:
            return b
    return boards[0] if boards else {}


def default_board_id() -> str:
    boards = list_boards()
    if not boards:
        return "esp32-devkit-v1"
    return boards[0].get("id", "esp32-devkit-v1")
