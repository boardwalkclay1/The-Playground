# backend/generator/modules/db_d1.py
from ..base import GenContext, FileOps, GenModule


class D1DatabaseModule(GenModule):
  """
  Describes a D1 schema for the app.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    schema_sql = """-- D1 schema placeholder
-- TODO: add tables per app domain.
"""
    FileOps.write_file(root / "schema.d1.sql", schema_sql, ctx)

    ctx.log("D1 schema stub created.")
