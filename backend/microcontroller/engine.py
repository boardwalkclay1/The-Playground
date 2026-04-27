"""
ESP Workbench Engine
Generates real ESP32 / ESP8266 / ESP32-C3 firmware from HTML/CSS/JS.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json
import shutil

from .settings import (
    MCUSettings,
    ensure_project_settings,
    load_settings,
    save_settings,
)
from .templates import (
    load_template,
    list_templates,
)
from .boards import (
    get_board,
    list_boards,
    default_board_id,
)
from .templates import (
    load_template,
)
from . import templates as template_module


# ---------------------------------------------------------
# ROOT
# ---------------------------------------------------------

MCU_ROOT = Path("backend/projects/mcu-sandbox")
MCU_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def _project_dir(project_name: str) -> Path:
    return MCU_ROOT / project_name


def _atomic_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


# ---------------------------------------------------------
# HTML/CSS/JS → ESP32 Arduino Sketch
# ---------------------------------------------------------

def build_single_page(html: str, css: str, js: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<style>
{css}
</style>
</head>
<body>
{html}
<script>
{js}
</script>
</body>
</html>
"""


def generate_arduino_sketch(html: str, css: str, js: str, board_id: str) -> str:
    page = build_single_page(html, css, js)

    return f"""
#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

WebServer server(80);

const char MAIN_page[] PROGMEM = R"rawliteral(
{page}
)rawliteral";

void handleRoot() {{
  server.send(200, "text/html", MAIN_page);
}}

void setup() {{
  Serial.begin(115200);
  delay(1000);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {{
    delay(500);
  }}

  server.on("/", handleRoot);
  server.begin();
}}

void loop() {{
  server.handleClient();
}}
""".strip()


# ---------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------

def generate_firmware(
    project_name: str,
    html: str,
    css: str,
    js: str,
    board_id: Optional[str] = None,
) -> Dict[str, Any]:

    # Prepare project directory
    project_dir = _project_dir(project_name)
    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Determine board
    if not board_id:
        board_id = default_board_id()

    board = get_board(board_id)

    # Ensure settings exist
    settings = ensure_project_settings(project_dir, board_id)

    # Generate firmware
    sketch = generate_arduino_sketch(html, css, js, board_id)

    # Write firmware file
    sketch_path = project_dir / "src" / "main.cpp"
    _atomic_write(sketch_path, sketch)

    # Save settings
    save_settings(project_dir, settings)

    return {
        "success": True,
        "project": project_name,
        "board": board,
        "settings": json.loads(settings.json()),
        "files": ["src/main.cpp"],
        "path": str(project_dir),
    }


def list_firmware_templates() -> Dict[str, Any]:
    return {"success": True, "templates": list_templates()}


def load_firmware_template(template_id: str) -> Dict[str, Any]:
    tmpl = load_template(template_id)
    if not tmpl:
        return {"success": False, "error": "Template not found"}
    return {"success": True, "template": tmpl}


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
    current = load_settings(project_dir) or ensure_project_settings(project_dir)

    updated = MCUSettings(
        board_id=new_settings.get("board_id", current.board_id),
        baud_rate=new_settings.get("baud_rate", current.baud_rate),
        flash_mode=new_settings.get("flash_mode", current.flash_mode),
        flash_freq=new_settings.get("flash_freq", current.flash_freq),
        upload_port=new_settings.get("upload_port", current.upload_port),
    )

    save_settings(project_dir, updated)

    return {"success": True, "settings": json.loads(updated.json())}
