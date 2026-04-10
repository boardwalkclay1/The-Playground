# backend/generator/modules/ai_assistant.py
from pathlib import Path
from ..base import GenContext, FileOps, GenModule


class AIAssistantModule(GenModule):
  """
  Adds a control file + hooks so the 'assistant' can:
  - read/write files
  - log actions
  - later: run commands, debug, etc.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    control_md = """# AI Assistant Control

This file marks this project as manageable by the Boardwalk AI assistant.

The assistant can:
- Read and write files in this project
- Propose changes
- Log actions
- (Later) run commands, debug errors, and refactor code.
"""
    FileOps.write_file(root / "AI_ASSISTANT.md", control_md, ctx)
    ctx.log("AI assistant control file created.")
