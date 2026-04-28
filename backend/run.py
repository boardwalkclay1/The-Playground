# run.py — Start backend + open frontend automatically

import webbrowser
import subprocess
import time
import sys
import os

def main():
    # Backend URL
    url = "http://localhost:8000"

    # Launch backend server
    print("Starting backend server...")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    )

    # Give server a moment to start
    time.sleep(2)

    # Open browser
    print("Opening frontend...")
    webbrowser.open(url)

    # Keep process alive
    try:
        process.wait()
    except KeyboardInterrupt:
        print("Shutting down...")
        process.terminate()

if __name__ == "__main__":
    main()
