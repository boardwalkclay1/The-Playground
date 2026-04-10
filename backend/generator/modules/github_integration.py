# backend/generator/modules/github_integration.py
from ..base import GenContext, FileOps, GenModule


class GitHubIntegrationModule(GenModule):
  """
  GitHub integration metadata (later: actual repo creation / sync).
  """

  def run(self, ctx: GenContext) -> None:
    root = ctx.project_path

    gh_json = """{
  "enabled": false,
  "repo": null
}
"""
    FileOps.write_file(root / "github.json", gh_json, ctx)
    ctx.log("GitHub integration stub created.")
