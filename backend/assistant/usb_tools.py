# backend/assistant/usb_tools.py
from ..usb import list_usb_mounts, export_project_to_usb

def assistant_list_usb() -> list[dict]:
    return list_usb_mounts()

def assistant_export_to_usb(project_root: str, usb_path: str, folder_name: str | None = None) -> dict:
    return export_project_to_usb(project_root, usb_path, folder_name)
