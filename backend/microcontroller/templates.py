from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import time
import shutil


# ---------------------------------------------------------
# ROOT PATHS
# ---------------------------------------------------------

MCU_ROOT = Path("backend/projects/mcu-sandbox")
LIB_ROOT = MCU_ROOT / "library"
TEMPLATES_ROOT = LIB_ROOT / "templates"
INDEX_PATH = LIB_ROOT / "library_index.json"

LIB_ROOT.mkdir(parents=True, exist_ok=True)
TEMPLATES_ROOT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_index() -> Dict[str, Any]:
    if not INDEX_PATH.exists():
        return {"templates": []}

    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"templates": []}


def _save_index(data: Dict[str, Any]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX_PATH.with_suffix(".tmp")

    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(INDEX_PATH)


# ---------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------

def list_templates() -> List[Dict[str, Any]]:
    idx = _load_index()
    return idx.get("templates", [])


def load_template(template_id: str) -> Optional[Dict[str, Any]]:
    idx = _load_index()

    for t in idx.get("templates", []):
        if t.get("id") == template_id:
            folder = TEMPLATES_ROOT / template_id
            files: Dict[str, str] = {}

            if folder.exists():
                for p in folder.rglob("*"):
                    if p.is_file():
                        rel = p.relative_to(folder).as_posix()
                        try:
                            files[rel] = p.read_text(encoding="utf-8")
                        except Exception:
                            files[rel] = ""

            out = dict(t)
            out["files"] = files
            return out

    return None


def save_template(
    template_id: str,
    name: str,
    description: str,
    tags: List[str],
    files: Dict[str, str],
    board_id: Optional[str] = None,
) -> None:

    # Load index
    idx = _load_index()
    templates = idx.get("templates", [])

    # Remove old entry
    templates = [t for t in templates if t.get("id") != template_id]

    # New metadata
    meta = {
        "id": template_id,
        "name": name,
        "description": description,
        "tags": tags,
        "board_id": board_id,
        "updated_at": _now_iso(),
    }

    templates.append(meta)
    idx["templates"] = templates

    # Save index
    _save_index(idx)

    # Save template files
    folder = TEMPLATES_ROOT / template_id

    if folder.exists():
        shutil.rmtree(folder)

    folder.mkdir(parents=True, exist_ok=True)

    for rel, content in files.items():
        safe_rel = rel.lstrip("/").replace("..", "")
        p = folder / safe_rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


# ---------------------------------------------------------
# DEFAULT BUILT-IN TEMPLATES (OPTIONAL)
# ---------------------------------------------------------

def ensure_default_templates():
    """
    Creates built-in templates if none exist.
    These are used by the ESP engine as base examples.
    """

    if list_templates():
        return  # Already have templates

    save_template(
        template_id="esp32-basic-web",
        name="ESP32 Basic Web Server",
        description="Minimal ESP32 web server serving a static HTML page.",
        tags=["esp32", "web", "basic"],
        board_id="esp32",
        files={
            "main.cpp": """#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

WebServer server(80);

const char MAIN_page[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head><title>ESP32</title></head>
<body><h1>Hello from ESP32</h1></body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", MAIN_page);
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  server.on("/", handleRoot);
  server.begin();
}

void loop() {
  server.handleClient();
}
"""
        },
    )

    save_template(
        template_id="micropython-basic",
        name="MicroPython Basic Web Server",
        description="Simple MicroPython web server example.",
        tags=["micropython", "esp32", "web"],
        board_id="esp32",
        files={
            "main.py": """import network
import socket
import time

ssid = "YOUR_WIFI_SSID"
password = "YOUR_WIFI_PASSWORD"

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected():
    time.sleep(0.5)

html = """<!DOCTYPE html>
<html>
<head><title>ESP32</title></head>
<body><h1>Hello from MicroPython</h1></body>
</html>"""

addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

while True:
    cl, addr = s.accept()
    req = cl.recv(1024)
    cl.send("HTTP/1.1 200 OK\\r\\nContent-Type: text/html\\r\\n\\r\\n")
    cl.send(html)
    cl.close()
"""
        },
    )


# Ensure defaults exist
ensure_default_templates()
