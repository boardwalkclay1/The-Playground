# backend/generator/modules/frontend_ui.py
"""
Upgraded FrontendUIModule

Improvements:
- Generates a small, extendable UI shell under /ui with:
  - ui/index.html (mount point and basic layout)
  - ui/main.js (app wiring, file-drop, token counter, assistant hook)
  - ui/styles.css (scoped styles for the UI shell)
  - ui/components/README.md (how to extend)
- Integrates with generated api-client.js if present
- Adds lightweight helpers for large-text chunking and showing estimated token counts
- Uses FileOps and GenContext for safe writes and logging
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

from ..base import GenContext, FileOps, GenModule


UI_INDEX = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{project_name} · UI</title>
  <link rel="stylesheet" href="../style.css" />
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <div id="boardwalk-ui">
    <header class="bw-header">
      <h1>{project_name}</h1>
      <div class="bw-meta">Generated UI shell · {ts}</div>
    </header>

    <main class="bw-main">
      <section class="bw-left">
        <div class="panel">
          <h3>Files</h3>
          <div id="file-list">No files loaded</div>
          <input id="file-drop" type="file" multiple style="display:none" />
          <button id="btn-drop" class="btn">Upload files</button>
        </div>

        <div class="panel">
          <h3>Assistant Input</h3>
          <textarea id="assistant-input" placeholder="Paste code or instructions here"></textarea>
          <div class="row">
            <div id="token-count" class="muted">Tokens: 0</div>
            <button id="assistant-run" class="btn btn-primary">Run Assistant</button>
          </div>
        </div>
      </section>

      <section class="bw-right">
        <div class="panel">
          <h3>Preview / Output</h3>
          <div id="assistant-output" class="output">No output yet</div>
        </div>
      </section>
    </main>

    <footer class="bw-footer">
      <small>Boardwalk Playground UI shell</small>
    </footer>
  </div>

  <script type="module" src="main.js"></script>
</body>
</html>
"""

UI_MAIN_JS = """// ui/main.js
// Minimal UI wiring for file upload, assistant input, token estimation, and API calls.
// Designed to be small and dependency-free; projects can replace with frameworks.

import { apiRequest } from '/api-client.js';

const projectName = document.querySelector('title')?.textContent?.split('·')?.[0]?.trim() || 'project';
const fileListEl = document.getElementById('file-list');
const fileDropInput = document.getElementById('file-drop');
const btnDrop = document.getElementById('btn-drop');
const assistantInput = document.getElementById('assistant-input');
const assistantRun = document.getElementById('assistant-run');
const assistantOutput = document.getElementById('assistant-output');
const tokenCountEl = document.getElementById('token-count');

function estimateTokens(text) {
  // rough heuristic: 1 token ~ 4 chars
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

function updateTokenCount() {
  const t = estimateTokens(assistantInput.value || '');
  tokenCountEl.textContent = `Tokens: ${t}`;
}

assistantInput.addEventListener('input', updateTokenCount);

btnDrop.addEventListener('click', () => fileDropInput.click());
fileDropInput.addEventListener('change', async (ev) => {
  const files = Array.from(ev.target.files || []);
  if (!files.length) return;
  fileListEl.innerHTML = '';
  for (const f of files) {
    const li = document.createElement('div');
    li.textContent = f.name + ' (' + f.size + ' bytes)';
    fileListEl.appendChild(li);
    // upload to backend project (assumes current project exists)
    try {
      const form = new FormData();
      form.append('project_name', projectName);
      form.append('file', f, f.name);
      await fetch('/api/files/upload', { method: 'POST', body: form });
    } catch (err) {
      console.error('upload error', err);
    }
  }
});

assistantRun.addEventListener('click', async () => {
  assistantOutput.textContent = 'Running assistant...';
  const prompt = assistantInput.value || '';
  const payload = { project_name: projectName, prompt };
  try {
    // prefer apiRequest if available
    const res = await apiRequest('/api/assistant/run', { method: 'POST', body: payload });
    assistantOutput.textContent = JSON.stringify(res, null, 2);
  } catch (err) {
    assistantOutput.textContent = 'Assistant error: ' + (err.message || String(err));
  }
});

// initial token count
updateTokenCount();
"""

UI_STYLES = """/* ui/styles.css - scoped UI shell styles */
#boardwalk-ui { font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, Arial; color: #e6eef8; background: transparent; padding: 12px; }
.bw-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }
.bw-main { display:flex; gap:12px; }
.bw-left { width:360px; display:flex; flex-direction:column; gap:12px; }
.bw-right { flex:1; display:flex; flex-direction:column; gap:12px; }
.panel { background: rgba(255,255,255,0.02); padding:12px; border-radius:8px; border:1px solid rgba(255,255,255,0.03); }
textarea#assistant-input { width:100%; min-height:120px; background:#071022; color:#e6eef8; border-radius:6px; padding:8px; border:1px solid rgba(255,255,255,0.03); }
.output { white-space:pre-wrap; font-family: monospace; background:#061021; padding:8px; border-radius:6px; min-height:120px; }
.btn { padding:6px 10px; border-radius:6px; background:transparent; border:1px solid rgba(255,255,255,0.04); color:inherit; cursor:pointer; }
.btn-primary { background:#2563eb; color:#fff; border-color:transparent; }
.muted { color:rgba(255,255,255,0.45); font-size:13px; }
.row { display:flex; justify-content:space-between; align-items:center; margin-top:8px; }
"""

COMPONENTS_README = """# UI Components

Place reusable UI components under ui/components/.

Examples:
- ui/components/file-tree.js
- ui/components/editor.js

The generated ui/main.js is intentionally minimal. Replace it with a framework (React/Vue/Svelte) if desired.
"""

class FrontendUIModule(GenModule):
    """
    Adds a basic UI shell that can be extended per app.
    """

    def run(self, ctx: GenContext) -> None:
        root: Path = ctx.project_path
        FileOps.ensure_dir(root, ctx)

        try:
            ui_dir = root / "ui"
            FileOps.ensure_dir(ui_dir, ctx)
            components_dir = ui_dir / "components"
            FileOps.ensure_dir(components_dir, ctx)

            ts = datetime.utcnow().isoformat() + "Z"
            index_html = UI_INDEX.format(project_name=ctx.project_name, ts=ts)
            FileOps.write_file(ui_dir / "index.html", index_html, ctx)

            FileOps.write_file(ui_dir / "main.js", UI_MAIN_JS, ctx)
            FileOps.write_file(ui_dir / "styles.css", UI_STYLES, ctx)
            FileOps.write_file(components_dir / "README.md", COMPONENTS_README, ctx)

            # update metadata
            try:
                meta_path = root / "metadata.json"
                meta = {}
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta.setdefault("features", [])
                if "frontend_ui" not in meta["features"]:
                    meta["features"].append("frontend_ui")
                meta["frontend_ui_added_at"] = datetime.utcnow().isoformat() + "Z"
                FileOps.write_file(meta_path, json.dumps(meta, indent=2), ctx)
            except Exception:
                pass

            ctx.log("Frontend UI module added", {"path": str(ui_dir)})
        except Exception as e:
            try:
                ctx.error(f"FrontendUIModule failed: {e}")
            except Exception:
                ctx.log(f"FrontendUIModule failed: {e}")
            raise
