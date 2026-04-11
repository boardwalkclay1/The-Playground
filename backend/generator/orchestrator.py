# backend/generator/orchestrator.py

from typing import List, Type
from .base import GenContext, GenResult, GenModule

# CORE MODULES (universal building blocks)
from .modules.project_scaffold import ProjectScaffoldModule
from .modules.frontend_ui import FrontendUIModule
from .modules.backend_service import BackendServiceModule
from .modules.worker_cloudflare import WorkerCloudflareModule
from .modules.api_client import APIClientModule
from .modules.db_d1 import D1DatabaseModule
from .modules.storage_r2 import R2StorageModule
from .modules.storage_kv import KVStorageModule
from .modules.github_integration import GitHubIntegrationModule
from .modules.auth_security import AuthSecurityModule
from .modules.ai_assistant import AIAssistantModule

# PYTHON + GIT + REPO UI ENGINES
from .python_generator import generate_python_app, generate_python_backend
from .git_clone import clone_repo
from .repo_ui import build_repo_ui

"""
IMPORTANT:
This orchestrator is the MASTER CONTROLLER.

It does 3 things:

1. Creates a GenContext (prompt, project_name, app_type)
2. Runs every core module in order OR dispatches to a specialized engine
3. Returns a GenResult with logs + errors

This is the UNIVERSAL GENERATOR ENGINE.
"""

# ORDER MATTERS — this is the build pipeline
CORE_MODULES: List[Type[GenModule]] = [
    ProjectScaffoldModule,     # Base project structure
    FrontendUIModule,          # Generic UI shell
    BackendServiceModule,      # Backend service descriptor
    WorkerCloudflareModule,    # Worker + wrangler
    APIClientModule,           # API client
    D1DatabaseModule,          # D1 schema stub
    R2StorageModule,           # R2 config stub
    KVStorageModule,           # KV config stub
    GitHubIntegrationModule,   # GitHub metadata
    AuthSecurityModule,        # Auth + hash seed
    AIAssistantModule,         # AI assistant control file
]


def _result_from_dict(ctx: GenContext, project_name: str, ok: bool, payload: dict) -> GenResult:
    if ok:
        ctx.log("Specialized generator completed successfully.")
    else:
        ctx.error("Specialized generator reported failure.")
        ctx.errors.append(str(payload.get("error") or "Unknown error"))
    return GenResult(
        success=ok,
        project_name=project_name,
        logs=ctx.logs,
        errors=ctx.errors,
    )


def run_universal_generator(prompt: str, project_name: str, app_type: str) -> GenResult:
    """
    The main entry point for generating ANY app.

    - Creates context
    - For known special types, dispatches to dedicated engines
    - Otherwise runs all core modules in order
    - Collects logs + errors
    - Returns a GenResult
    """

    ctx = GenContext(
        prompt=prompt,
        project_name=project_name,
        app_type=app_type,
    )

    try:
        ctx.log(f"Starting universal generator for project='{project_name}', type='{app_type}'")

        # ----------------------------------------------------
        # SPECIALIZED ENGINES
        # ----------------------------------------------------
        if app_type == "python-app":
            ctx.log("Dispatching to Python App generator engine.")
            payload = generate_python_app(ctx.project_root, project_name, {"prompt": prompt, "app_type": app_type})
            return _result_from_dict(ctx, project_name, bool(payload.get("ok")), payload)

        if app_type == "python-backend":
            ctx.log("Dispatching to Python Backend generator engine.")
            payload = generate_python_backend(ctx.project_root, project_name, {"prompt": prompt, "app_type": app_type})
            return _result_from_dict(ctx, project_name, bool(payload.get("ok")), payload)

        if app_type == "git-clone":
            # Convention: prompt carries git_url, project_name is target folder
            ctx.log(f"Dispatching to Git clone engine for repo='{prompt}'.")
            try:
                payload = clone_repo(ctx.project_root, prompt, project_name or None)
                return _result_from_dict(ctx, project_name or payload.get("project_name", ""), True, payload)
            except Exception as e:
                ctx.error(f"Git clone failed: {e}")
                return GenResult(
                    success=False,
                    project_name=project_name,
                    logs=ctx.logs,
                    errors=ctx.errors,
                )

        if app_type == "repo-ui":
            # Convention: prompt carries relative repo folder under project root
            ctx.log(f"Dispatching to Repo UI builder for folder='{prompt}'.")
            repo_root = (ctx.project_root / prompt).as_posix()
            payload = build_repo_ui(repo_root)
            ok = payload is not None
            return _result_from_dict(ctx, project_name, ok, payload or {"error": "Repo UI build failed"})

        # ----------------------------------------------------
        # DEFAULT UNIVERSAL PIPELINE
        # ----------------------------------------------------
        for module_cls in CORE_MODULES:
            module = module_cls()
            ctx.log(f"Running module: {module_cls.__name__}")
            module.run(ctx)

        success = len(ctx.errors) == 0

        if success:
            ctx.log("Generation completed successfully.")
        else:
            ctx.error("Generation completed with errors.")

        return GenResult(
            success=success,
            project_name=project_name,
            logs=ctx.logs,
            errors=ctx.errors,
        )

    except Exception as e:
        ctx.error(f"UNHANDLED EXCEPTION in generator: {e}")
        return GenResult(
            success=False,
            project_name=project_name,
            logs=ctx.logs,
            errors=ctx.errors,
        )
