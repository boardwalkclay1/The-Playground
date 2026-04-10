# backend/generator/modules/worker_cloudflare.py
from ..base import GenContext, FileOps, GenModule


class WorkerCloudflareModule(GenModule):
  """
  Creates a basic Cloudflare Worker + wrangler config.
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    worker_js = """export default {
  async fetch(request, env, ctx) {
    return new Response("Worker for generated app is alive.", { status: 200 });
  }
};
"""
    FileOps.write_file(root / "worker.js", worker_js, ctx)

    wrangler_toml = f"""name = "{ctx.project_name}-worker"
main = "worker.js"
compatibility_date = "2024-01-01"
"""
    FileOps.write_file(root / "wrangler.toml", wrangler_toml, ctx)

    ctx.log("Cloudflare Worker + wrangler config created.")
