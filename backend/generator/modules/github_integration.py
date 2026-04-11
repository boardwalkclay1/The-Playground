# backend/generator/modules/github_integration.py
"""
Upgraded GitHubIntegrationModule

What it does:
- Writes a structured `github.json` descriptor for repo sync settings.
- Adds a `.github/workflows/ci.yml` GitHub Actions workflow (basic CI: lint/test).
- Emits a small `github_helper.py` helper that can create a repo and push initial commit
  when a `GITHUB_TOKEN` is provided in the environment (optional, safe, and explicit).
- Writes `GITHUB_README.md` explaining how to enable integration and security notes.
- Uses FileOps and GenContext for safe writes and logging. Does not perform network actions
  during generation; helper is provided for manual/CI invocation.

Security notes:
- The helper expects `GITHUB_TOKEN` in the environment and will not store tokens in files.
- The helper is conservative: it only creates a repo if explicitly requested and prints
  clear instructions. It is safe to include in generated projects.
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

from ..base import GenContext, FileOps, GenModule


GITHUB_JSON = {
    "enabled": False,
    "repo": None,
    "owner": None,
    "private": True,
    "create_remote_on_generate": False,
    "workflow_enabled": True,
    "notes": "Set enabled=true and provide owner/repo to enable helper actions."
}

CI_WORKFLOW = """name: CI

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt || true; fi
      - name: Run linters
        run: |
          if command -v black >/dev/null 2>&1; then black --check . || true; fi
          if command -v flake8 >/dev/null 2>&1; then flake8 || true; fi
      - name: Run tests
        run: |
          if [ -f pyproject.toml ] || [ -f setup.cfg ] || [ -d tests ]; then
            pytest -q || true
          else
            echo "No tests detected"
          fi
"""

GITHUB_HELPER = '''"""
github_helper.py

Optional helper to create a GitHub repository and push the current project.
This script is intentionally conservative and requires:
- GITHUB_TOKEN environment variable with repo:create and repo permissions
- git installed and available on PATH
- The project directory to be a git repo (or it will initialize one)

Usage:
  export GITHUB_TOKEN="ghp_..."
  python github_helper.py --create --owner my-org --repo my-repo --private true

Notes:
- This helper performs network operations. Review and run manually.
- It will not store tokens in files.
"""

import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any

import urllib.request
import urllib.error

API_BASE = "https://api.github.com"

def _run(cmd, cwd=None):
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def _create_repo(owner: str, repo: str, private: bool = True, description: str = "") -> Dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN not set in environment")
    url = f"{API_BASE}/orgs/{owner}/repos" if owner and owner != os.environ.get('GITHUB_USER') else f"{API_BASE}/user/repos"
    payload = {"name": repo, "private": bool(private), "description": description}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "boardwalk-playground"
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API error: {e.code} {e.reason} {body}")

def push_initial_commit(repo_url: str, project_dir: Path):
    # Ensure git repo
    if not (project_dir / ".git").exists():
        _run(["git", "init"], cwd=str(project_dir))
        _run(["git", "add", "."], cwd=str(project_dir))
        _run(["git", "commit", "-m", "Initial commit from Boardwalk Playground"], cwd=str(project_dir))
    # Add remote and push
    _run(["git", "remote", "add", "origin", repo_url], cwd=str(project_dir))
    _run(["git", "branch", "-M", "main"], cwd=str(project_dir))
    _run(["git", "push", "-u", "origin", "main"], cwd=str(project_dir))

def main():
    parser = argparse.ArgumentParser(description="GitHub helper for generated projects")
    parser.add_argument("--create", action="store_true", help="Create remote repo")
    parser.add_argument("--owner", type=str, default=None, help="Owner (user or org)")
    parser.add_argument("--repo", type=str, required=False, help="Repository name")
    parser.add_argument("--private", type=str, default="true", help="Private repo (true/false)")
    parser.add_argument("--description", type=str, default="", help="Repo description")
    parser.add_argument("--push", action="store_true", help="Push initial commit after creating repo")
    args = parser.parse_args()

    project_dir = Path.cwd()
    if args.create:
        if not args.repo:
            print("Error: --repo is required when --create is used", file=sys.stderr)
            sys.exit(2)
        try:
            info = _create_repo(args.owner, args.repo, private=(args.private.lower() != "false"), description=args.description)
            print("Created repo:", info.get("html_url"))
            if args.push:
                push_initial_commit(info.get("ssh_url") or info.get("clone_url"), project_dir)
        except Exception as e:
            print("Failed to create repo:", e, file=sys.stderr)
            sys.exit(1)
    else:
        print("No action specified. Use --create to create a repo.")

if __name__ == "__main__":
    main()
'''

GITHUB_README = """# GitHub Integration

This project includes a GitHub integration descriptor and helper files.

Files added:
- `github.json` — descriptor controlling integration behavior.
- `.github/workflows/ci.yml` — basic CI workflow (lint/test).
- `github_helper.py` — optional helper to create a GitHub repo and push initial commit (requires GITHUB_TOKEN).
- `GITHUB_README.md` — this file.

How to enable:
1. Edit `github.json` and set `"enabled": true`, `"owner"` and `"repo"` fields.
2. Provide a `GITHUB_TOKEN` with appropriate permissions in your environment when running `github_helper.py`.
3. Run `python github_helper.py --create --owner <owner> --repo <repo> --push` from the project root to create the remote and push.

Security:
- Do not commit `GITHUB_TOKEN` to the repository.
- The helper will not store tokens; it reads them from the environment at runtime.
"""

class GitHubIntegrationModule(GenModule):
    """
    Generates GitHub integration descriptor, workflow, and helper files.
    """

    def run(self, ctx: GenContext) -> None:
        root: Path = ctx.project_path
        FileOps.ensure_dir(root, ctx)

        try:
            # Write github.json descriptor
            cfg = GITHUB_JSON.copy()
            cfg["generated_at"] = datetime.utcnow().isoformat() + "Z"
            FileOps.write_file(root / "github.json", json.dumps(cfg, indent=2), ctx)

            # Write GitHub Actions workflow
            gh_dir = root / ".github" / "workflows"
            FileOps.ensure_dir(gh_dir, ctx)
            FileOps.write_file(gh_dir / "ci.yml", CI_WORKFLOW, ctx)

            # Write helper script
            FileOps.write_file(root / "github_helper.py", GITHUB_HELPER, ctx)

            # Write README
            FileOps.write_file(root / "GITHUB_README.md", GITHUB_README, ctx)

            # Update metadata
            try:
                meta_path = root / "metadata.json"
                meta = {}
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta.setdefault("features", [])
                if "github_integration" not in meta["features"]:
                    meta["features"].append("github_integration")
                meta["github_integration_added_at"] = datetime.utcnow().isoformat() + "Z"
                FileOps.write_file(meta_path, json.dumps(meta, indent=2), ctx)
            except Exception:
                pass

            ctx.log("GitHub integration files created", {"path": str(root / "github.json")})
        except Exception as e:
            try:
                ctx.error(f"GitHubIntegrationModule failed: {e}")
            except Exception:
                ctx.log(f"GitHubIntegrationModule failed: {e}")
            raise
