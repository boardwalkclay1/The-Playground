# backend/microcontroller/breadboard_sim.py

from pathlib import Path
from typing import Dict, Any, List
import json

MCU_ROOT = Path("backend/projects/mcu-sandbox")
DATA_ROOT = MCU_ROOT / "data"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

COMPONENTS_PATH = DATA_ROOT / "components.json"
RULES_PATH = DATA_ROOT / "rules.json"


# ---------------------------------------------------------
# DEFAULT COMPONENT + RULE DATABASE
# ---------------------------------------------------------

_DEFAULT_COMPONENTS = {
    "components": [
        {"type": "led", "max_current_ma": 20, "forward_voltage": 2.0},
        {"type": "resistor", "min_ohm": 1, "max_ohm": 10_000_000},
        {"type": "capacitor", "min_uF": 0.0001, "max_uF": 10000},
        {"type": "button", "max_current_ma": 50},
        {"type": "sensor-dht11", "voltage_min": 3.0, "voltage_max": 5.5},
        {"type": "sensor-dht22", "voltage_min": 3.0, "voltage_max": 6.0},
        {"type": "oled-ssd1306", "voltage_min": 3.0, "voltage_max": 5.0},
        {"type": "servo", "voltage_min": 4.8, "voltage_max": 6.0, "max_current_ma": 500},
        {"type": "motor-dc", "voltage_min": 3.0, "voltage_max": 12.0, "max_current_ma": 1500},
    ]
}

_DEFAULT_RULES = {
    "max_vcc": 5.5,
    "min_vcc": 1.8,
    "esp32_max_pin_current_ma": 12,
    "led_series_resistor_min_ohm": 100,
    "short_circuit_threshold_ohm": 5,
}


# ---------------------------------------------------------
# FILE HANDLING
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# SIMULATION ENGINE
# ---------------------------------------------------------

def simulate_circuit(netlist: Dict[str, Any]) -> Dict[str, Any]:
    components_db = _load_components()
    rules = _load_rules()

    vcc = float(netlist.get("vcc", 3.3))
    issues: List[str] = []
    warnings: List[str] = []

    # -----------------------------
    # VCC RANGE CHECK
    # -----------------------------
    if vcc > rules["max_vcc"]:
        issues.append(f"VCC {vcc}V exceeds max {rules['max_vcc']}V")
    if vcc < rules["min_vcc"]:
        issues.append(f"VCC {vcc}V below min {rules['min_vcc']}V")

    # -----------------------------
    # COMPONENT + CONNECTION MAPS
    # -----------------------------
    comps = {c["id"]: c for c in netlist.get("components", []) if "id" in c}
    conns = netlist.get("connections", [])

    # -----------------------------
    # HELPER: find all connections for a component
    # -----------------------------
    def _connections_for(cid: str) -> List[Dict[str, str]]:
        out = []
        for c in conns:
            if cid in c.get("from", "") or cid in c.get("to", ""):
                out.append(c)
        return out

    # -----------------------------
    # LED RULES
    # -----------------------------
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
                issues.append(f"LED {led_id} has no series resistor")

    # -----------------------------
    # RESISTOR VALUE CHECKS
    # -----------------------------
    for c in comps.values():
        if c.get("type") == "resistor":
            ohm = c.get("value_ohm")
            if ohm is None:
                warnings.append(f"Resistor {c['id']} has no value_ohm")
                continue

            if ohm < rules["led_series_resistor_min_ohm"]:
                warnings.append(f"Resistor {c['id']} value {ohm}Ω is very low")

            if ohm < rules["short_circuit_threshold_ohm"]:
                issues.append(f"Resistor {c['id']} value {ohm}Ω may cause a short circuit")

    # -----------------------------
    # SENSOR VOLTAGE CHECKS
    # -----------------------------
    for c in comps.values():
        ctype = c.get("type")
        for db in components_db["components"]:
            if db["type"] == ctype:
                vmin = db.get("voltage_min")
                vmax = db.get("voltage_max")
                if vmin and vcc < vmin:
                    issues.append(f"{ctype} {c['id']} requires >= {vmin}V")
                if vmax and vcc > vmax:
                    issues.append(f"{ctype} {c['id']} exceeds max voltage {vmax}V")

    # -----------------------------
    # SHORT CIRCUIT DETECTION
    # -----------------------------
    for conn in conns:
        f = conn.get("from", "")
        t = conn.get("to", "")

        if ("3V3" in f and "GND" in t) or ("3V3" in t and "GND" in f):
            issues.append("Direct short between 3V3 and GND")

    # -----------------------------
    # OUTPUT
    # -----------------------------
    return {
        "ok": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "vcc": vcc,
    }
