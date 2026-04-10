# backend/generator/modules/storage_r2.py
from ..base import GenContext, FileOps, GenModule


class R2StorageModule(GenModule):
  """
  R2 bucket config stub.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    r2_json = """{
  "buckets": [
    { "name": "media", "purpose": "app media storage" }
  ]
}
"""
    FileOps.write_file(root / "r2-config.json", r2_json, ctx)
    ctx.log("R2 storage config stub created.")
