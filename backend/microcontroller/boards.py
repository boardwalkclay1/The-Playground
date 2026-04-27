# backend/microcontroller/boards.py

from pathlib import Path
from typing import Dict, Any, List
import json

# ---------------------------------------------------------
# ROOT PATHS
# ---------------------------------------------------------

MCU_ROOT = Path("backend/projects/mcu-sandbox")
DATA_ROOT = MCU_ROOT / "data"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

BOARDS_PATH = DATA_ROOT / "boards_index.json"


# ---------------------------------------------------------
# DEFAULT BOARD DEFINITIONS
# ---------------------------------------------------------

_DEFAULT_BOARDS = {
    "boards": [
        {
            "id": "esp32-devkit-v1",
            "name": "ESP32 DevKit V1",
            "vendor": "Espressif",
            "fqbn": "esp32:esp32:esp32",
            "voltage": 3.3,
            "max_current_ma": 500,
            "flash_mode": "dio",
            "flash_freq": "40m",
            "default_baud": 115200,
            "capabilities": {
                "adc": True,
                "dac": True,
                "wifi": True,
                "bt": True,
                "spi": True,
                "i2c": True,
                "uart": True,
                "pwm": True,
            },
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
        },
        {
            "id": "esp32-c3",
            "name": "ESP32-C3 DevKit",
            "vendor": "Espressif",
            "fqbn": "esp32:esp32:esp32c3",
            "voltage": 3.3,
            "max_current_ma": 500,
            "flash_mode": "dio",
            "flash_freq": "80m",
            "default_baud": 460800,
            "capabilities": {
                "adc": True,
                "dac": False,
                "wifi": True,
                "bt": True,
                "spi": True,
                "i2c": True,
                "uart": True,
                "pwm": True,
            },
            "pins": {
                "3V3": "3.3V output",
                "GND": "Ground",
                "GPIO0": "Boot / IO",
                "GPIO1": "TX",
                "GPIO2": "IO",
                "GPIO3": "RX",
                "GPIO4": "IO",
                "GPIO5": "IO",
                "GPIO6": "IO",
                "GPIO7": "IO",
                "GPIO8": "IO",
                "GPIO9": "IO",
                "GPIO10": "IO",
            },
        },
        {
            "id": "esp32-s3",
            "name": "ESP32-S3 DevKit",
            "vendor": "Espressif",
            "fqbn": "esp32:esp32:esp32s3",
            "voltage": 3.3,
            "max_current_ma": 500,
            "flash_mode": "qio",
            "flash_freq": "80m",
            "default_baud": 921600,
            "capabilities": {
                "adc": True,
                "dac": False,
                "wifi": True,
                "bt": True,
                "spi": True,
                "i2c": True,
                "uart": True,
                "pwm": True,
                "usb": True,
            },
            "pins": {
                "3V3": "3.3V output",
                "GND": "Ground",
                "GPIO1": "IO",
                "GPIO2": "IO",
                "GPIO3": "IO",
                "GPIO4": "IO",
                "GPIO5": "IO",
                "GPIO6": "IO",
                "GPIO7": "IO",
                "GPIO8": "IO",
                "GPIO9": "IO",
                "GPIO10": "IO",
                "GPIO11": "IO",
                "GPIO12": "IO",
                "GPIO13": "IO",
                "GPIO14": "IO",
                "GPIO15": "IO",
                "GPIO16": "IO",
                "GPIO17": "IO",
                "GPIO18": "IO",
                "GPIO19": "IO",
                "GPIO20": "IO",
                "GPIO21": "IO",
            },
        },
        {
            "id": "esp8266-nodemcu",
            "name": "ESP8266 NodeMCU",
            "vendor": "Espressif",
            "fqbn": "esp8266:esp8266:nodemcuv2",
            "voltage": 3.3,
            "max_current_ma": 300,
            "flash_mode": "dout",
            "flash_freq": "40m",
            "default_baud": 115200,
            "capabilities": {
                "adc": True,
                "dac": False,
                "wifi": True,
                "bt": False,
                "spi": True,
                "i2c": True,
                "uart": True,
                "pwm": True,
            },
            "pins": {
                "3V3": "3.3V output",
                "GND": "Ground",
                "D0": "GPIO16",
                "D1": "GPIO5",
                "D2": "GPIO4",
                "D3": "GPIO0",
                "D4": "GPIO2",
                "D5": "GPIO14",
                "D6": "GPIO12",
                "D7": "GPIO13",
                "D8": "GPIO15",
                "A0": "ADC",
            },
        },
        {
            "id": "esp32-wroom",
            "name": "ESP32 WROOM Module",
            "vendor": "Espressif",
            "fqbn": "esp32:esp32:esp32",
            "voltage": 3.3,
            "max_current_ma": 500,
            "flash_mode": "dio",
            "flash_freq": "40m",
            "default_baud": 115200,
            "capabilities": {
                "adc": True,
                "dac": True,
                "wifi": True,
                "bt": True,
                "spi": True,
                "i2c": True,
                "uart": True,
                "pwm": True,
            },
            "pins": {
                "GPIO0": "Boot / IO",
                "GPIO1": "TX",
                "GPIO2": "LED / IO",
                "GPIO3": "RX",
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
            },
        },
    ]
}


# ---------------------------------------------------------
# FILE HANDLING
# ---------------------------------------------------------

def _ensure_boards_file():
    if not BOARDS_PATH.exists():
        BOARDS_PATH.write_text(json.dumps(_DEFAULT_BOARDS, indent=2), encoding="utf-8")


def _load_boards() -> Dict[str, Any]:
    _ensure_boards_file()
    try:
        return json.loads(BOARDS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _DEFAULT_BOARDS


# ---------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------

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
