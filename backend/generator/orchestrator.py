# backend/generator/orchestrator.py

from typing import List, Type, Dict, Any
import os
import openai

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
SUPER APP GENERATOR ORCHESTRATOR

This is the master controller for full-stack app generation.

- Uses an LLM planner to design the app (frontend, backend, workers, Cloudflare, GitHub, etc.)
- Runs your existing modules as the build pipeline
- Still supports specialized engines (python-app, python-backend, git-clone, repo-ui)
"""

openai.api_key = os.getenv("OPENAI_API_KEY")

MODELS: Dict[str, str] = {
    "planner": "gpt-4o",
}

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


def _plan_app_with_llm(prompt: str, project_name: str, app_type: str) -> Dict[str, Any]:
    """
    Use GPT-4o as a planner to design the full app:
    - architecture
    - folders
    - files
    - frontend/backend/worker responsibilities
    - Cloudflare + GitHub integration
    """
    system = (
        "You are the Boardwalk Playground SUPER APP PLANNER.\n"
        "You design complete full-stack web apps that will be built by a module pipeline.\n"
        "The environment has these capabilities:\n"
        "- Project scaffold (folders, base files)\n"
        "- Frontend UI shell (index.html, app shell, basic layout)\n"
        "- Backend service descriptor (API endpoints, routes, handlers)\n"
        "- Cloudflare Worker + wrangler config\n"
        "- API client for frontend\n"
        "- D1 database schema stub\n"
        "- R2 storage config stub\n"
        "- KV storage config stub\n"
        "- GitHub metadata (repo info, CI hints)\n"
        "- Auth + security seeds\n"
        "- AI assistant control file\n\n"
        "Your job is to output a concise JSON plan describing:\n"
        "- high_level_goal: one sentence\n"
        "- architecture: short description\n"
        "- frontend: key pages/components\n"
        "- backend: key routes/services\n"
        "- worker: what the worker does\n"
        "- data: main entities/tables\n"
        "- github: repo/CI notes\n"
        "- notes: any extra constraints\n"
        "Keep it compact but concrete. This plan will be logged and used by modules."
    )

    user = (
        f"Project name: {project_name}\n"
        f"App type: {app_type}\n"
        f"User prompt: {prompt}\n\n"
        "Return ONLY a JSON object. No prose, no markdown."
    )

    resp = openai.chat.completions.create(
        model=MODELS["planner"],
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )

    content = resp.choices[0].message.content or "{}"
    try:
        plan = json.loads(content)
    except Exception:
        # Fallback: wrap raw content
        plan = {"raw_plan": content}
    return plan


def run_universal_generator(prompt: str, project_name: str, app_type: str) -> GenResult:
    """
    SUPER APP GENERATOR ENTRYPOINT

    - Creates context
    - Uses LLM to plan the app (full-stack, workers, Cloudflare, GitHub, etc.)
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
        ctx.log(f"Starting SUPER app generator for project='{project_name}', type='{app_type}'")

        # ----------------------------------------------------
        # LLM PLANNING PHASE (for all app types)
        # ----------------------------------------------------
        try:
            plan = _plan_app_with_llm(prompt, project_name, app_type)
            # Attach plan to context so modules can optionally use it
            setattr(ctx, "plan", plan)
            ctx.log("LLM app plan generated.")
            ctx.log(f"LLM PLAN (summary): {plan.get('high_level_goal', '')}")
        except Exception as e:
            ctx.error(f"LLM planning failed: {e}")
            setattr(ctx, "plan", {"error": str(e)})

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
        # DEFAULT FULL-STACK PIPELINE (USES MODULES)
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

        return GenResult(
            success=success,
            project_name=project_name,
            logs=ctx.logs,
            errors=ctx.errors,
        )

    except Exception as e:
        ctx.error(f"UNHANDLED EXCEPTION in SUPER generator: {e}")
        return GenResult(
            success=False,
            project_name=project_name,
            logs=ctx.logs,
            errors=ctx.errors,
        )
