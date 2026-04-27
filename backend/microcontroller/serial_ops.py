# backend/microcontroller/serial_ops.py

import sys
import glob
from typing import List, Dict, Any


def list_serial_ports() -> Dict[str, Any]:
    """
    Cross‑platform serial port detection.
    """
    ports: List[str] = []

    if sys.platform.startswith("win"):
        ports = [f"COM{i}" for i in range(1, 256)]

    elif sys.platform.startswith("linux"):
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")

    elif sys.platform.startswith("darwin"):
        ports = glob.glob("/dev/cu.*")

    out = []
    for p in ports:
        out.append({"device": p})

    return {"success": True, "ports": out}
