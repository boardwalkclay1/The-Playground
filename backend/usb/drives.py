# backend/usb/drives.py
import os
from pathlib import Path

def list_usb_mounts() -> list[dict]:
    """
    Very simple heuristic: list mount points under /media, /mnt, /Volumes.
    You can harden this per OS.
    """
    candidates = [Path("/media"), Path("/mnt"), Path("/Volumes")]
    mounts = []

    for base in candidates:
        if not base.exists():
            continue
        for child in base.iterdir():
            if child.is_dir():
                mounts.append({
                    "path": str(child),
                    "label": child.name,
                })

    return mounts
