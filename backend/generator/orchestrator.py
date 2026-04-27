# backend/generator/orchestrator.py

from typing import List, Type, Dict, Any
import json
import traceback

from openai_client import fused_chat

from .base import GenContext, GenResult, GenModule

# CORE MODULES
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

# SPECIAL ENGINES
from .python_generator import generate_python_app, generate_python_backend
from .git_clone import clone_repo
from .repo_ui import build_repo_ui


# -----------------------------------------------------------
# ORDERED PIPELINE
# -----------------------------------------------------------

CORE_MODULES: List[Type[GenModule]] = [
    ProjectScaffoldModule,
    FrontendUIModule,
    BackendServiceModule,
    WorkerCloudflareModule,
    APIClientModule,
    D1DatabaseModule,
    R2StorageModule,
    KVStorageModule,
    GitHubIntegrationModule,
    AuthSecurityModule,
    AIAssistantModule,
]


# -----------------------------------------------------------
# LLM PLANNER (HARDENED)
# -----------------------------------------------------------

def _plan_app(prompt: str, project_name: str, app_type: str) -> Dict[str, Any]:
    """
    Deterministic LLM planner.
    Always returns a valid JSON object.
    Never crashes the generator.
    """

    system = (
        "You are the Boardwalk SUPER APP PLANNER.\n"
        "Return ONLY a JSON object.\n"
        "No prose. No markdown. No commentary.\n"
        "If unsure, return minimal valid JSON.\n"
    )

    user = (
        f"Project: {project_name}\n"
        f"Type: {app_type}\n"
        f"Prompt: {prompt}\n"
        "Return ONLY JSON.\n"
    )

    try:
        raw = fused_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])

        try:
            return json.loads(raw)
        except Exception:
            return {"raw": raw, "error": "Invalid JSON returned"}

    except Exception as e:
        return {"error": f"Planner failed: {e}"}


# -----------------------------------------------------------
# SPECIAL ENGINE WRAPPER
# -----------------------------------------------------------

def _wrap_special(ctx: GenContext, project_name: str, payload: Dict[str, Any]) -> GenResult:
    ok = bool(payload.get("ok") or payload.get("success"))
    if ok:
        ctx.log("Specialized engine completed successfully.")
    else:
        ctx.error("Specialized engine failed.")
        ctx.errors.append(str(payload.get("error") or "Unknown error"))

    return GenResult(
        success=ok,
        project_name=project_name,
        logs=ctx.logs,
        errors=ctx.errors,
    )


# -----------------------------------------------------------
# MAIN UNIVERSAL GENERATOR
# -----------------------------------------------------------

def run_universal_generator(prompt: str, project_name: str, app_type: str) -> GenResult:
    ctx = GenContext(prompt=prompt, project_name=project_name, app_type=app_type)

    try:
        ctx.log(f"Starting SUPER generator for '{project_name}' ({app_type})")

        # ----------------------------------------------------
        # LLM PLANNING
        # ----------------------------------------------------
        plan = _plan_app(prompt, project_name, app_type)
        ctx.plan = plan
        ctx.log("LLM plan generated.")

        # ----------------------------------------------------
        # SPECIALIZED ENGINES
        # ----------------------------------------------------

        if app_type == "python-app":
            ctx.log("Running Python App generator engine.")
            payload = generate_python_app(ctx.project_root, project_name, {"prompt": prompt})
            return _wrap_special(ctx, project_name, payload)

        if app_type == "python-backend":
            ctx.log("Running Python Backend generator engine.")
            payload = generate_python_backend(ctx.project_root, project_name, {"prompt": prompt})
            return _wrap_special(ctx, project_name, payload)

        if app_type == "git-clone":
            ctx.log(f"Cloning repo: {prompt}")
            try:
                payload = clone_repo(ctx.project_root, prompt, project_name)
                return _wrap_special(ctx, project_name, payload)
            except Exception as e:
                ctx.error(f"Git clone failed: {e}")
                return GenResult(False, project_name, ctx.logs, ctx.errors)

        if app_type == "repo-ui":
            ctx.log(f"Building Repo UI for folder='{prompt}'")
            repo_root = (ctx.project_root / prompt).as_posix()
            payload = build_repo_ui(repo_root)
            ok = payload is not None
            return _wrap_special(ctx, project_name, payload or {"error": "Repo UI build failed"})

        # ----------------------------------------------------
        # DEFAULT FULL-STACK PIPELINE
        # ----------------------------------------------------
        ctx.log("Running full-stack module pipeline.")

        for module_cls in CORE_MODULES:
            module = module_cls()
            ctx.log(f"Running module: {module_cls.__name__}")
            module.run(ctx)

        success = len(ctx.errors) == 0

        if success:
            ctx.log("SUPER app generation completed successfully.")
        else:
            ctx.error("SUPER app generation completed with errors.")

        return GenResult(success, project_name, ctx.logs, ctx.errors)

    except Exception as e:
        ctx.error(f"UNHANDLED EXCEPTION: {e}")
        ctx.error(traceback.format_exc())
        return GenResult(False, project_name, ctx.logs, ctx.errors)
