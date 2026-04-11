# backend/microcontroller/breadboard_sim.py
"""
Simple rule-based breadboard simulator core.

Input netlist example:
{
  "board_id": "esp32-devkit-v1",
  "vcc": 5.0,
  "components": [
    {"id": "led1", "type": "led", "value": null},
    {"id": "r1", "type": "resistor", "value_ohm": 330}
  ],
  "connections": [
    {"from": "3V3", "to": "r1.1"},
    {"from": "r1.2", "to": "led1.anode"},
    {"from": "led1.cathode", "to": "GND"}
  ]
}
"""

from pathlib import Path
from typing import Dict, Any, List
import json

MCU_ROOT = Path("projects/mcu-sandbox")
DATA_ROOT = MCU_ROOT / "data"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

COMPONENTS_PATH = DATA_ROOT / "components.json"
RULES_PATH = DATA_ROOT / "rules.json"


_DEFAULT_COMPONENTS = {
    "components": [
        {"type": "led", "max_current_ma": 20, "forward_voltage": 2.0},
        {"type": "resistor", "min_ohm": 1, "max_ohm": 10_000_000},
        {"type": "capacitor", "min_uF": 0.0001, "max_uF": 10000},
        {"type": "button", "max_current_ma": 50},
        {"type": "sensor-dht11", "voltage_min": 3.0, "voltage_max": 5.5},
        {"type": "sensor-dht22", "voltage_min": 3.0, "voltage_max": 6.0},
        {"type": "oled-ssd1306", "voltage_min": 3.0, "voltage_max": 5.0},
    ]
}

_DEFAULT_RULES = {
    "max_vcc": 5.5,
    "min_vcc": 1.8,
    "led_series_resistor_min_ohm": 100,
    "esp32_max_pin_current_ma": 12,
}


def _ensure_files():
    if not COMPONENTS_PATH.exists():
        COMPONENTS_PATH.write_text(json.dumps(_DEFAULT_COMPONENTS, indent=2), encoding="utf-8")
    if not RULES_PATH.exists():
        RULES_PATH.write_text(json.dumps(_DEFAULT_RULES, indent=2), encoding="utf-8")


def _load_components() -> Dict[str, Any]:
    _ensure_files()
    try:
        return json.loads(COMPONENTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _DEFAULT_COMPONENTS


def _load_rules() -> Dict[str, Any]:
    _ensure_files()
    try:
        return json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return _DEFAULT_RULES


def simulate_circuit(netlist: Dict[str, Any]) -> Dict[str, Any]:
    components_db = _load_components()
    rules = _load_rules()

    vcc = float(netlist.get("vcc", 3.3))
    issues: List[str] = []
    warnings: List[str] = []

    if vcc > rules["max_vcc"]:
        issues.append(f"VCC {vcc}V exceeds max {rules['max_vcc']}V")
    if vcc < rules["min_vcc"]:
        issues.append(f"VCC {vcc}V below min {rules['min_vcc']}V")

    comps = {c["id"]: c for c in netlist.get("components", []) if "id" in c}
    conns = netlist.get("connections", [])

    # Very simple LED rule: LED between VCC and GND must have series resistor
    for c in comps.values():
        if c.get("type") == "led":
            led_id = c["id"]
            series_resistor_found = False
            for r in comps.values():
                if r.get("type") == "resistor":
                    rid = r["id"]
                    for conn in conns:
                        if led_id in conn.get("from", "") or led_id in conn.get("to", ""):
                            if rid in conn.get("from", "") or rid in conn.get("to", ""):
                                series_resistor_found = True
                                break
                    if series_resistor_found:
                        break
            if not series_resistor_found:
                issues.append(f"LED {led_id} appears to be connected without a series resistor")

    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "vcc": vcc,
    }
