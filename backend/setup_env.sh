#!/usr/bin/env bash
set -e

# 1) create and activate venv (POSIX)
cd backend

python3 -m venv .venv
# POSIX activation
source .venv/bin/activate

# 2) upgrade pip and install requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3) verify uvicorn and fastapi
python -c "import fastapi, uvicorn; print('fastapi', fastapi.__version__, 'uvicorn OK')"

echo "Backend virtualenv created at backend/.venv and packages installed."
echo "Activate with: source backend/.venv/bin/activate"
