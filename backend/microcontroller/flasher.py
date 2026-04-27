# backend/microcontroller/flasher.py

from pathlib import Path
from typing import Dict, Any, Optional
import subprocess
import shutil
import json

from .settings import load_settings
from .serial_ops import list_serial_ports
from .boards import get_board

MCU_ROOT = Path("backend/projects/mcu-sandbox")


def _run(cmd: list, cwd: Optional[str] = None) -> Dict[str, Any]:
    """
    Run a subprocess and return structured output.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, err = proc.communicate()

        return {
            "success": proc.returncode == 0,
            "stdout": out,
            "stderr": err,
            "returncode": proc.returncode,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def flash_project_firmware(
    project_name: str,
    port: Optional[str] = None,
    erase: bool = False
) -> Dict[str, Any]:

    project_dir = MCU_ROOT / project_name
    src_dir = project_dir / "src"
    sketch = src_dir / "main.cpp"

    if not sketch.exists():
        return {"success": False, "error": "No firmware found (main.cpp missing)"}

    settings = load_settings(project_dir)
    if not settings:
        return {"success": False, "error": "No MCU settings found"}

    board = get_board(settings.board_id)
    fqbn = board["fqbn"]

    # Detect port if not provided
    if not port:
        ports = list_serial_ports().get("ports", [])
        if not ports:
            return {"success": False, "error": "No serial ports detected"}
        port = ports[0]["device"]

    # Compile
    compile_cmd = [
        "arduino-cli", "compile",
        "--fqbn", fqbn,
        str(project_dir)
    ]

    compile_res = _run(compile_cmd)
    if not compile_res["success"]:
        return {
            "success": False,
            "error": "Compilation failed",
            "details": compile_res,
        }

    # Upload
    upload_cmd = [
        "arduino-cli", "upload",
        "-p", port,
        "--fqbn", fqbn,
        str(project_dir)
    ]

    if erase:
        upload_cmd.insert(2, "--erase")

    upload_res = _run(upload_cmd)

    if not upload_res["success"]:
        return {
            "success": False,
            "error": "Upload failed",
            "details": upload_res,
        }

    return {
        "success": True,
        "message": "Firmware flashed successfully",
        "compile": compile_res,
        "upload": upload_res,
        "port": port,
        "board": board,
    }
