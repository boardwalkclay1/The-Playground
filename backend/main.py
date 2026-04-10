import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
PROJECTS_DIR = os.path.join(FRONTEND_DIR, "projects")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def ensure_projects_dir():
    os.makedirs(PROJECTS_DIR, exist_ok=True)

@app.get("/")
def root():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/editor")
def editor_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "editor.html"))

@app.get("/cloudflare")
def cloudflare_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "cloudflare.html"))

@app.get("/capabilities")
def capabilities_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "capabilities.html"))

@app.get("/plugins")
def plugins_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "plugins.html"))

@app.get("/logs")
def logs_page():
    return FileResponse(os.path.join(FRONTEND_DIR, "logs.html"))

@app.get("/static/{path:path}")
def static_files(path: str):
    return FileResponse(os.path.join(FRONTEND_DIR, "static", path))

# ---------- PROJECTS & FILES ----------

@app.get("/api/projects")
def api_projects():
    ensure_projects_dir()
    items = []
    for name in os.listdir(PROJECTS_DIR):
        full = os.path.join(PROJECTS_DIR, name)
        if os.path.isdir(full):
            items.append(name)
    return {"projects": sorted(items)}

@app.get("/api/files/tree")
def api_files_tree(project: str):
    ensure_projects_dir()
    root = os.path.join(PROJECTS_DIR, project)
    if not os.path.isdir(root):
        return {"items": []}
    items = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        for d in dirnames:
            items.append({"type": "dir", "path": os.path.join(rel_dir, d).replace("\\", "/")})
        for f in filenames:
            items.append({"type": "file", "path": os.path.join(rel_dir, f).replace("\\", "/")})
    return {"items": items}

@app.get("/api/files/read")
def api_files_read(project: str, path: str):
    ensure_projects_dir()
    full = os.path.join(PROJECTS_DIR, project, path)
    if not os.path.isfile(full):
        return {"content": ""}
    with open(full, "r", encoding="utf-8") as f:
        return {"content": f.read()}

@app.post("/api/files/write")
async def api_files_write(request: Request):
    ensure_projects_dir()
    data = await request.json()
    project = data["project"]
    path = data["path"]
    content = data["content"]
    full = os.path.join(PROJECTS_DIR, project, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "ok"}

# ---------- RUN / DEPLOY ----------

@app.post("/api/run/backend")
async def api_run_backend(request: Request):
    data = await request.json()
    project = data.get("project")
    print(f"[RUN] Backend for {project}")
    return {"status": "started", "kind": "backend", "project": project}

@app.post("/api/run/frontend")
async def api_run_frontend(request: Request):
    data = await request.json()
    project = data.get("project")
    print(f"[RUN] Frontend for {project}")
    return {"status": "started", "kind": "frontend", "project": project}

# ---------- CLOUDFLARE ----------

@app.post("/api/cloudflare/deploy_worker")
async def api_cf_deploy_worker(request: Request):
    data = await request.json()
    project = data.get("project")
    events = [
        {"kind": "info", "message": f"Deploying Worker for {project}"},
        {"kind": "success", "message": "Worker deployed (mock)."},
    ]
    return {"events": events}

@app.post("/api/cloudflare/deploy_pages")
async def api_cf_deploy_pages(request: Request):
    data = await request.json()
    project = data.get("project")
    events = [
        {"kind": "info", "message": f"Deploying Pages for {project}"},
        {"kind": "success", "message": "Pages deployed (mock)."},
    ]
    return {"events": events}

@app.post("/api/cloudflare/create_d1")
async def api_cf_create_d1(request: Request):
    data = await request.json()
    project = data.get("project")
    return {"events": [{"kind": "success", "message": f"D1 created for {project} (mock)."}]}

@app.post("/api/cloudflare/create_r2")
async def api_cf_create_r2(request: Request):
    data = await request.json()
    project = data.get("project")
    return {"events": [{"kind": "success", "message": f"R2 created for {project} (mock)."}]}

@app.post("/api/cloudflare/create_kv")
async def api_cf_create_kv(request: Request):
    data = await request.json()
    project = data.get("project")
    return {"events": [{"kind": "success", "message": f"KV created for {project} (mock)."}]}

@app.post("/api/cloudflare/create_queue")
async def api_cf_create_queue(request: Request):
    data = await request.json()
    project = data.get("project")
    return {"events": [{"kind": "success", "message": f"Queue created for {project} (mock)."}]}

# ---------- GITHUB ----------

@app.post("/api/github/clone")
async def api_github_clone(request: Request):
    data = await request.json()
    project = data.get("project")
    repo_url = data.get("repo_url")
    events = [
        {"kind": "info", "message": f"Cloning {repo_url} into {project} (mock)."},
        {"kind": "success", "message": "Clone completed (mock)."},
    ]
    return {"events": events}

# ---------- CAPABILITIES / PLUGINS / LOGS ----------

@app.get("/api/capabilities")
def api_capabilities():
    return {
        "capabilities": [
            {"name": "File Tree", "description": "Browse and edit project files."},
            {"name": "Editor", "description": "Full-page code editor."},
            {"name": "Cloudflare Suite", "description": "Deploy Workers, Pages, and resources."},
            {"name": "GitHub Clone", "description": "Clone repos into projects."},
            {"name": "Run / Deploy", "description": "Trigger backend/frontend runs."},
            {"name": "Plugins", "description": "Extend Boardwalk Playground with custom tools."},
        ]
    }

@app.get("/api/plugins")
def api_plugins():
    return {
        "plugins": [
            {"name": "Arborist Lessons", "kind": "education"},
            {"name": "Skater Flows", "kind": "media"},
            {"name": "Trading Sandbox", "kind": "finance"},
        ]
    }

@app.get("/api/logs")
def api_logs():
    # placeholder
    return {"lines": ["[LOG] Boardwalk Playground ready."]}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
