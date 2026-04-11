#!/usr/bin/env bash
set -e

echo "=== Boardwalk Backend Setup ==="

# -------------------------------
# 1) Enter backend folder
# -------------------------------
cd backend

# -------------------------------
# 2) Create + activate venv
# -------------------------------
if [ ! -d ".venv" ]; then
  echo "[+] Creating virtualenv..."
  python3 -m venv .venv
fi

echo "[+] Activating virtualenv..."
source .venv/bin/activate

# -------------------------------
# 3) Upgrade pip + install deps
# -------------------------------
echo "[+] Upgrading pip..."
python -m pip install --upgrade pip

echo "[+] Installing backend requirements..."
pip install -r requirements.txt

# -------------------------------
# 4) Verify core backend modules
# -------------------------------
echo "[+] Verifying FastAPI + Uvicorn..."
python - << 'EOF'
import fastapi, uvicorn
print("FastAPI:", fastapi.__version__)
print("Uvicorn OK")
EOF

# -------------------------------
# 5) Verify MCU toolchain
# -------------------------------
echo "[+] Checking esptool..."
python -m esptool version || echo "WARNING: esptool not found"

echo "[+] Checking PlatformIO..."
platformio --version || echo "WARNING: PlatformIO not installed or not in PATH"

# -------------------------------
# 6) Verify Git availability
# -------------------------------
echo "[+] Checking Git..."
git --version || echo "WARNING: Git not installed"

# -------------------------------
# 7) Verify Cloudflare Wrangler
# -------------------------------
echo "[+] Checking Wrangler..."
wrangler --version || echo "WARNING: Wrangler not installed"

# -------------------------------
# 8) Verify Node/NPM (for Pages builds)
# -------------------------------
echo "[+] Checking Node..."
node --version || echo "WARNING: Node not installed"

echo "[+] Checking NPM..."
npm --version || echo "WARNING: NPM not installed"

# -------------------------------
# 9) Validate assistant-config.json
# -------------------------------
echo "[+] Validating assistant-config.json..."
python - << 'EOF'
import json, sys
from pathlib import Path

cfg = Path("assistant-config.json")
if not cfg.exists():
    print("WARNING: assistant-config.json missing")
    sys.exit(0)

try:
    json.loads(cfg.read_text())
    print("assistant-config.json OK")
except Exception as e:
    print("ERROR: assistant-config.json invalid:", e)
EOF

# -------------------------------
# DONE
# -------------------------------
echo ""
echo "=== Backend environment ready ==="
echo "Activate anytime with:"
echo "  source backend/.venv/bin/activate"
