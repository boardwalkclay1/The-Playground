# backend/assistant/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# =========================================================
# BASE RESPONSE
# =========================================================

class BaseResponse(BaseModel):
    success: bool = True
    action: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# =========================================================
# FILE OPERATIONS
# =========================================================

class CreateFileRequest(BaseModel):
    path: str = Field(..., description="Relative path inside project")
    content: Optional[str] = Field("", description="File content")
    overwrite: Optional[bool] = Field(False)


class EditFileRequest(BaseModel):
    path: str
    content: str
    create_backup: Optional[bool] = True


class DeleteRequest(BaseModel):
    path: str
    recursive: Optional[bool] = False


class MoveRequest(BaseModel):
    src: str
    dst: str
    overwrite: Optional[bool] = False


# =========================================================
# TERMINAL / COMMANDS
# =========================================================

class RunCommandRequest(BaseModel):
    command: str
    timeout_seconds: Optional[int] = 30


class TerminalRequest(BaseModel):
    project_name: str
    command: str
    timeout_seconds: Optional[int] = 30


# =========================================================
# PATCHING
# =========================================================

class PatchRequest(BaseModel):
    patch: str
    apply: Optional[bool] = False
    create_backup: Optional[bool] = True


# =========================================================
# AGENT RUN
# =========================================================

class AgentRunRequest(BaseModel):
    project_name: str
    prompt: str


# =========================================================
# PYTHON TOOLS
# =========================================================

class PythonExplainRequest(BaseModel):
    project_name: str
    path: str


class PythonGenerateRequest(BaseModel):
    project_name: str
    path: str
    description: str


class PythonRunRequest(BaseModel):
    project_name: str
    path: str


# =========================================================
# GIT TOOLS
# =========================================================

class GitCloneRequest(BaseModel):
    project_name: str
    git_url: str
    folder_name: str


# =========================================================
# REPO ANALYZER + REPO UI
# =========================================================

class AnalyzeRepoRequest(BaseModel):
    project_name: str
    folder: str


class BuildRepoUIRequest(BaseModel):
    project_name: str
    folder: str


# =========================================================
# USB TOOLS
# =========================================================

class USBListRequest(BaseModel):
    pass  # no fields needed


class USBExportRequest(BaseModel):
    project_name: str
    folder: str
    usb_path: str
