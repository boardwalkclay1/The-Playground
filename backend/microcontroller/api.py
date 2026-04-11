# backend/microcontroller/api.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from .engine import (
    generate_firmware,
    flash_firmware,
    simulate_breadboard,
    list_firmware_templates,
    load_firmware_template,
    save_firmware_template,
    list_supported_boards,
    get_board_settings,
    update_board_settings,
)

router = APIRouter(prefix="/mcu", tags=["mcu"])


# -------------------- MODELS --------------------

class GenerateRequest(BaseModel):
    project_name: str
    prompt: str
    template_id: Optional[str] = None
    board_id: Optional[str] = None
    merge_strategy: str = "overwrite"


class FlashRequest(BaseModel):
    project_name: str


class BreadboardRequest(BaseModel):
    project_name: str
    netlist: Dict[str, Any]


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


# -------------------- ROUTES --------------------

@router.get("/boards")
def mcu_boards():
    boards = list_supported_boards() or []
    if not isinstance(boards, list):
        boards = []
    return {"boards": boards}


@router.get("/templates")
def mcu_list_templates():
    templates = list_firmware_templates() or []
    if not isinstance(templates, list):
        templates = []
    return {"templates": templates}


@router.post("/generate")
def mcu_generate(req: GenerateRequest):
    return generate_firmware(
        project_name=req.project_name,
        prompt=req.prompt,
        template_id=req.template_id,
        board_id=req.board_id,
        merge_strategy=req.merge_strategy,
    )


@router.post("/flash")
def mcu_flash(req: FlashRequest):
    return flash_firmware(req.project_name)


@router.post("/simulate")
def mcu_simulate(req: BreadboardRequest):
    return simulate_breadboard(req.project_name, req.netlist)


@router.get("/templates/{template_id}")
def mcu_get_template(template_id: str):
    res = load_firmware_template(template_id)
    if not res or not res.get("success"):
        raise HTTPException(status_code=404, detail="Template not found")
    return res


@router.post("/templates")
def mcu_save_template(req: TemplateSaveRequest):
    return save_firmware_template(
        template_id=req.template_id,
        name=req.name,
        description=req.description,
        tags=req.tags,
        files=req.files,
        board_id=req.board_id,
    )


@router.get("/settings/{project_name}")
def mcu_get_settings(project_name: str):
    return get_board_settings(project_name)


@router.post("/settings")
def mcu_update_settings(req: SettingsUpdateRequest):
    return update_board_settings(req.project_name, req.settings)
