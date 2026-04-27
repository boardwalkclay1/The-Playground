from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from .engine import (
    generate_firmware,
    list_firmware_templates,
    load_firmware_template,
)
from .settings import (
    get_board_settings,
    update_board_settings,
)
from .boards import (
    list_boards,
)
from .flasher import (
    flash_project_firmware,
)
from .serial_ops import (
    list_serial_ports,
)


router = APIRouter(prefix="/mcu", tags=["mcu"])


# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------

class GenerateRequest(BaseModel):
    project_name: str
    html: str
    css: str
    js: str
    board_id: Optional[str] = None


class FlashRequest(BaseModel):
    project_name: str
    port: Optional[str] = None
    erase: bool = False


class TemplateSaveRequest(BaseModel):
    template_id: str
    name: str
    description: str
    tags: List[str]
    files: Dict[str, str]
    board_id: Optional[str] = None


class SettingsUpdateRequest(BaseModel):
    project_name: str
    settings: Dict[str, Any]


# ---------------------------------------------------------
# ROUTES
# ---------------------------------------------------------

@router.get("/boards")
def mcu_boards():
    """Return supported boards."""
    return {"success": True, "boards": list_boards()}


@router.get("/ports")
def mcu_ports():
    """Return available serial ports."""
    return {"success": True, "ports": list_serial_ports()}


@router.get("/templates")
def mcu_list_templates():
    """Return firmware templates."""
    return list_firmware_templates()


@router.get("/templates/{template_id}")
def mcu_get_template(template_id: str):
    """Return a specific template."""
    res = load_firmware_template(template_id)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail="Template not found")
    return res


@router.post("/generate")
def mcu_generate(req: GenerateRequest):
    """
    Generate ESP firmware from HTML/CSS/JS.
    """
    return generate_firmware(
        project_name=req.project_name,
        html=req.html,
        css=req.css,
        js=req.js,
        board_id=req.board_id,
    )


@router.post("/flash")
def mcu_flash(req: FlashRequest):
    """
    Flash compiled firmware to an ESP board.
    """
    result = flash_project_firmware(
        project_name=req.project_name,
        port=req.port,
        erase=req.erase,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))

    return result


@router.get("/settings/{project_name}")
def mcu_get_settings(project_name: str):
    """Return MCU settings for a project."""
    return get_board_settings(project_name)


@router.post("/settings")
def mcu_update_settings(req: SettingsUpdateRequest):
    """Update MCU settings for a project."""
    return update_board_settings(req.project_name, req.settings)
