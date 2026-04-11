# backend/usb/export.py
import shutil
from pathlib import Path

def export_project_to_usb(project_root: str, usb_path: str, folder_name: str | None = None) -> dict:
    src = Path(project_root)
    dst_base = Path(usb_path)

    if not src.exists():
        raise FileNotFoundError(f"Project root not found: {src}")
    if not dst_base.exists():
        raise FileNotFoundError(f"USB path not found: {dst_base}")

    if folder_name is None:
        folder_name = src.name

    dst = dst_base / folder_name

    if dst.exists():
        shutil.rmtree(dst)

    shutil.copytree(src, dst)

    return {
        "ok": True,
        "project_root": str(src),
        "usb_path": str(dst),
    }
