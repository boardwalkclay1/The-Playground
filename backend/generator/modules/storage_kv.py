# backend/generator/modules/storage_kv.py
from ..base import GenContext, FileOps, GenModule


class KVStorageModule(GenModule):
  """
  KV namespace config stub.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    kv_json = """{
  "namespaces": [
    { "name": "app-kv", "purpose": "generic key-value storage" }
  ]
}
"""
    FileOps.write_file(root / "kv-config.json", kv_json, ctx)
    ctx.log("KV storage config stub created.")
