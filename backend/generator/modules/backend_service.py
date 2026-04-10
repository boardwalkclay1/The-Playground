# backend/generator/modules/backend_service.py
from ..base import GenContext, FileOps, GenModule


class BackendServiceModule(GenModule):
  """
  Describes backend service contract for this app.
  (Later: map to Worker routes, FastAPI, etc.)
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    service_json = """{
  "services": [
    { "name": "default", "description": "Primary backend service", "routes": [] }
  ]
}
"""
    FileOps.write_file(root / "backend-services.json", service_json, ctx)
    ctx.log("Backend service descriptor created.")
