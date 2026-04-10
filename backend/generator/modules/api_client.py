# backend/generator/modules/api_client.py
from ..base import GenContext, FileOps, GenModule


class APIClientModule(GenModule):
  """
  Adds a generic API client for talking to Worker / external APIs.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    client_js = """// Generic API client
export async function apiRequest(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json().catch(() => null);
}
"""
    FileOps.write_file(root / "api-client.js", client_js, ctx)
    ctx.log("API client module added.")
