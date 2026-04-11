# backend/assistant/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class BaseResponse(BaseModel):
    success: bool = True
    action: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

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

class RunCommandRequest(BaseModel):
    command: str
    timeout_seconds: Optional[int] = 30

class AgentRunRequest(BaseModel):
    project_name: str
    prompt: str

class PatchRequest(BaseModel):
    patch: str
    apply: Optional[bool] = False
    create_backup: Optional[bool] = True

class TerminalRequest(BaseModel):
    project_name: str
    command: str
    timeout_seconds: Optional[int] = 30
