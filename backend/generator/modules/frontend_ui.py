# backend/generator/modules/frontend_ui.py
from ..base import GenContext, FileOps, GenModule


class FrontendUIModule(GenModule):
  """
  Adds a basic UI shell that can be extended per app.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    ui_js = """// Generic UI shell
console.log('Generic UI module loaded.');
// TODO: attach domain-specific components here.
"""
    FileOps.write_file(root / "ui-generic.js", ui_js, ctx)
    ctx.log("Frontend UI module added.")
