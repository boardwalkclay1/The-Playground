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


"""
IMPORTANT:
This orchestrator is the MASTER CONTROLLER.

It does 3 things:

1. Creates a GenContext (prompt, project_name, app_type)
2. Runs every core module in order
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


def run_universal_generator(prompt: str, project_name: str, app_type: str) -> GenResult:
    """
    The main entry point for generating ANY app.

    - Creates context
    - Runs all modules in order
    - Collects logs + errors
    - Returns a GenResult
    """

    ctx = GenContext(
        prompt=prompt,
        project_name=project_name,
        app_type=app_type
    )

    try:
        ctx.log(f"Starting universal generator for project='{project_name}', type='{app_type}'")

        # Run each module in sequence
        for module_cls in CORE_MODULES:
            module = module_cls()
            ctx.log(f"Running module: {module_cls.__name__}")
            module.run(ctx)

        # Final status
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
