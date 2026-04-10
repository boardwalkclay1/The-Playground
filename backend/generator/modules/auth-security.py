# backend/generator/modules/auth_security.py
from ..base import GenContext, FileOps, GenModule, hash_string


class AuthSecurityModule(GenModule):
  """
  Adds basic auth/security config and hash helpers.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    secret = hash_string(ctx.project_name + ctx.prompt)
    auth_json = f"""{{
  "auth_enabled": false,
  "hash_seed": "{secret}"
}}
"""
    FileOps.write_file(root / "auth-config.json", auth_json, ctx)
    ctx.log("Auth/security config stub created.")
