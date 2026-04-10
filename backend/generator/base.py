# backend/generator/base.py
from __future__ import annotations
import os
import hashlib
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Protocol, runtime_checkable

PROJECTS_ROOT = Path("projects")


@dataclass
class GenLog:
  level: str
  message: str


@dataclass
class GenResult:
  success: bool
  project_name: str
  logs: List[GenLog] = field(default_factory=list)
  errors: List[str] = field(default_factory=list)


class GenContext:
  def __init__(self, prompt: str, project_name: str, app_type: str, extras: Dict[str, Any] | None = None):
    self.prompt = prompt
    self.project_name = project_name
    self.app_type = app_type
    self.extras = extras or {}
    self.logs: List[GenLog] = []
    self.errors: List[str] = []

  def log(self, message: str, level: str = "info"):
    self.logs.append(GenLog(level=level, message=message))

  def error(self, message: str):
    self.logs.append(GenLog(level="error", message=message))
    self.errors.append(message)

  @property
  def project_path(self) -> Path:
    return PROJECTS_ROOT / self.project_name


class FileOps:
  @staticmethod
  def ensure_dir(path: Path, ctx: GenContext):
    if not path.exists():
      path.mkdir(parents=True, exist_ok=True)
      ctx.log(f"Created directory: {path}")
    else:
      ctx.log(f"Directory exists: {path}")

  @staticmethod
  def write_file(path: Path, content: str, ctx: GenContext, overwrite: bool = False):
    if path.exists() and not overwrite:
      ctx.log(f"File exists, skipping (no overwrite): {path}")
      return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    ctx.log(f"Wrote file: {path}")

  @staticmethod
  def read_file(path: Path, ctx: GenContext) -> str | None:
    if not path.exists():
      ctx.error(f"File not found: {path}")
      return None
    data = path.read_text(encoding="utf-8")
    ctx.log(f"Read file: {path}")
    return data


def hash_string(value: str) -> str:
  return hashlib.sha256(value.encode("utf-8")).hexdigest()


@runtime_checkable
class GenModule(Protocol):
  def run(self, ctx: GenContext) -> None:
    ...
