# backend/generator/orchestrator.py

from typing import List, Type, Dict, Any
import os, json

from openai_client import fused_chat   # <-- NEW SUPER ENGINE

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
# MODEL CONFIG
# -----------------------------------------------------------

MODELS: Dict[str, str] = {
    "planner": "gpt-4o",   # used only for naming; fused_chat overrides
}

# ORDERED PIPELINE
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
# HELPERS
# -----------------------------------------------------------

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


# -----------------------------------------------------------
# FUSED LLM PLANNER
# -----------------------------------------------------------

def _plan_app_with_llm(prompt: str, project_name: str, app_type: str) -> Dict[str, Any]:
    """
    Uses fused_chat to generate a JSON plan for the full-stack app.
    """

    system = (
        "You are the Boardwalk Playground SUPER APP PLANNER. "
        "Output ONLY a JSON object describing the app plan. "
        "No prose. No markdown."
    )

    user = (
        f"Project name: {project_name}\n"
        f"App type: {app_type}\n"
        f"User prompt: {prompt}\n"
        "Return ONLY JSON."
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    raw = fused_chat(messages)

    try:
        return json.loads(raw)
    except Exception:
        return {"raw_plan": raw}


# -----------------------------------------------------------
# MAIN GENERATOR
# -----------------------------------------------------------

def run_universal_generator(prompt: str, project_name: str, app_type: str) -> GenResult:
    ctx = GenContext(prompt=prompt, project_name=project_name, app_type=app_type)

    try:
        ctx.log(f"Starting SUPER generator for project='{project_name}', type='{app_type}'")

        # ----------------------------------------------------
        # LLM PLANNING PHASE
        # ----------------------------------------------------
        try:
            plan = _plan_app_with_llm(prompt, project_name, app_type)
            setattr(ctx, "plan", plan)
            ctx.log("LLM plan generated.")
            ctx.log(f"PLAN SUMMARY: {plan.get('high_level_goal', '')}")
        except Exception as e:
            ctx.error(f"LLM planning failed: {e}")
            setattr(ctx, "plan", {"error": str(e)})

        # ----------------------------------------------------
        # SPECIALIZED ENGINES
        # ----------------------------------------------------
        if app_type == "python-app":
            ctx.log("Running Python App generator engine.")
            payload = generate_python_app(ctx.project_root, project_name, {"prompt": prompt})
            return _result_from_dict(ctx, project_name, bool(payload.get("ok")), payload)

        if app_type == "python-backend":
            ctx.log("Running Python Backend generator engine.")
            payload = generate_python_backend(ctx.project_root, project_name, {"prompt": prompt})
            return _result_from_dict(ctx, project_name, bool(payload.get("ok")), payload)

        if app_type == "git-clone":
            ctx.log(f"Cloning repo: {prompt}")
            try:
                payload = clone_repo(ctx.project_root, prompt, project_name)
                return _result_from_dict(ctx, project_name, True, payload)
            except Exception as e:
                ctx.error(f"Git clone failed: {e}")
                return GenResult(False, project_name, ctx.logs, ctx.errors)

        if app_type == "repo-ui":
            ctx.log(f"Building Repo UI for folder='{prompt}'")
            repo_root = (ctx.project_root / prompt).as_posix()
            payload = build_repo_ui(repo_root)
            ok = payload is not None
            return _result_from_dict(ctx, project_name, ok, payload or {"error": "Repo UI build failed"})

        # ----------------------------------------------------
        # DEFAULT FULL-STACK PIPELINE
        # ----------------------------------------------------
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
        return GenResult(False, project_name, ctx.logs, ctx.errors)
