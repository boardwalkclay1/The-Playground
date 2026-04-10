const API_BASE = window.location.origin;

// ---------- THEME TOGGLE ----------

function initThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  const html = document.documentElement;

  function updateLabel() {
    const theme = html.getAttribute("data-theme") || "industrial";
    btn.textContent = `Theme: ${theme === "industrial" ? "Industrial" : "Neon"}`;
  }

  btn.onclick = () => {
    const current = html.getAttribute("data-theme") || "industrial";
    const next = current === "industrial" ? "neon" : "industrial";
    html.setAttribute("data-theme", next);
    updateLabel();
  };

  updateLabel();
}

// ---------- DASHBOARD PANELS ----------

async function initDashboard() {
  if (!document.body.classList.contains("layout-two-column")) return;

  initThemeToggle();
  await initPanelProjects();
  await initPanelFileTree();
  await initPanelPlugins();
  await initPanelCloudflareQuick();
  await initPanelRunDeploy();
  await initPanelCapabilitiesQuick();
  await initPanelPreview();
  initMainViewDefault();
}

async function initPanelProjects() {
  const container = document.getElementById("panel-projects");
  if (!container) return;

  const res = await fetch(`${API_BASE}/api/projects`);
  const data = await res.json();
  const projects = data.projects || [];

  container.innerHTML = `
    <h2>Projects</h2>
    <select id="dash-project-select" class="full-width">
      ${projects.map(p => `<option value="${p}">${p}</option>`).join("")}
    </select>
    <div class="small" style="margin-top:6px;">
      <a href="/editor">Open Editor Page</a>
    </div>
  `;
}

function getSelectedProject() {
  const sel = document.getElementById("dash-project-select");
  return sel ? sel.value : "";
}

async function initPanelFileTree() {
  const container = document.getElementById("panel-filetree");
  if (!container) return;

  container.innerHTML = `<h2>File Tree</h2><div id="filetree-list" class="small">Select a project.</div>`;

  const project = getSelectedProject();
  if (!project) return;

  const res = await fetch(`${API_BASE}/api/files/tree?project=${encodeURIComponent(project)}`);
  const data = await res.json();
  const items = data.items || [];

  const list = document.getElementById("filetree-list");
  list.innerHTML = items
    .map(i => {
      const icon = i.type === "dir" ? "📁" : "📄";
      const click = i.type === "file"
        ? `onclick="openFileInDashboard('${project}','${i.path.replace(/'/g, "\\'")}')"`
        : "";
      return `<div class="file-item" ${click}>${icon} ${i.path}</div>`;
    })
    .join("");
}

async function initPanelPlugins() {
  const container = document.getElementById("panel-plugins");
  if (!container) return;

  const res = await fetch(`${API_BASE}/api/plugins`);
  const data = await res.json();
  const plugins = data.plugins || [];

  container.innerHTML = `
    <h2>Plugins</h2>
    <div class="small">
      ${plugins.map(p => `<div>${p.name} <span style="opacity:.6">(${p.kind})</span></div>`).join("")}
    </div>
    <div class="small" style="margin-top:6px;">
      <a href="/plugins">Open Plugins Page</a>
    </div>
  `;
}

async function initPanelCloudflareQuick() {
  const container = document.getElementById("panel-cloudflare");
  if (!container) return;

  container.innerHTML = `
    <h2>Cloudflare</h2>
    <button class="btn btn-primary" id="quick-cf-worker">Deploy Worker</button>
    <button class="btn btn-primary" id="quick-cf-pages">Deploy Pages</button>
    <div class="small" style="margin-top:6px;">
      <a href="/cloudflare">Open Cloudflare Page</a>
    </div>
  `;

  const project = () => getSelectedProject() || "";

  document.getElementById("quick-cf-worker").onclick = async () => {
    const res = await fetch(`${API_BASE}/api/cloudflare/deploy_worker`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ project: project() })
    });
    const data = await res.json();
    pushMainLog("Cloudflare Worker (quick)", data.events || []);
  };

  document.getElementById("quick-cf-pages").onclick = async () => {
    const res = await fetch(`${API_BASE}/api/cloudflare/deploy_pages`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ project: project() })
    });
    const data = await res.json();
    pushMainLog("Cloudflare Pages (quick)", data.events || []);
  };
}

async function initPanelRunDeploy() {
  const container = document.getElementById("panel-rundeploy");
  if (!container) return;

  container.innerHTML = `
    <h2>Run / Deploy</h2>
    <button class="btn btn-primary" id="quick-run-backend">▶ Backend</button>
    <button class="btn btn-primary" id="quick-run-frontend">▶ Frontend</button>
    <div class="small" style="margin-top:6px;">
      Uses current project selection.
    </div>
  `;

  const project = () => getSelectedProject() || "";

  document.getElementById("quick-run-backend").onclick = async () => {
    const res = await fetch(`${API_BASE}/api/run/backend`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ project: project() })
    });
    const data = await res.json();
    pushMainLog("Run Backend", [{kind: "info", message: JSON.stringify(data)}]);
  };

  document.getElementById("quick-run-frontend").onclick = async () => {
    const res = await fetch(`${API_BASE}/api/run/frontend`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ project: project() })
    });
    const data = await res.json();
    pushMainLog("Run Frontend", [{kind: "info", message: JSON.stringify(data)}]);
  };
}

async function initPanelCapabilitiesQuick() {
  const container = document.getElementById("panel-capabilities");
  if (!container) return;

  const res = await fetch(`${API_BASE}/api/capabilities`);
  const data = await res.json();
  const caps = data.capabilities || [];

  container.innerHTML = `
    <h2>Capabilities</h2>
    <div class="small">
      ${caps.map(c => `<div>${c.name}</div>`).join("")}
    </div>
    <div class="small" style="margin-top:6px;">
      <a href="/capabilities">Open Capabilities Page</a>
    </div>
  `;
}

async function initPanelPreview() {
  const container = document.getElementById("panel-preview");
  if (!container) return;

  container.innerHTML = `
    <h2>Preview</h2>
    <iframe class="preview-frame" src="about:blank"></iframe>
    <div class="small" style="margin-top:6px;">
      You can point this iframe to any local app later.
    </div>
  `;
}

function initMainViewDefault() {
  const container = document.getElementById("panel-main-view");
  if (!container) return;

  container.innerHTML = `
    <h2>Boardwalk Playground</h2>
    <div class="small">
      Select a file from the File Tree to open it in the inline editor,
      or open the full Editor page for deep work.
    </div>
    <div style="margin-top:10px;">
      <textarea id="editor-text-dashboard" placeholder="Inline editor (dashboard)"></textarea>
    </div>
  `;
}

// ---------- INLINE EDITOR FROM FILE TREE ----------

window.openFileInDashboard = async function(project, path) {
  const res = await fetch(`${API_BASE}/api/files/read?project=${encodeURIComponent(project)}&path=${encodeURIComponent(path)}`);
  const data = await res.json();
  const container = document.getElementById("panel-main-view");
  if (!container) return;

  container.innerHTML = `
    <h2>${project} · ${path}</h2>
    <div class="small" style="margin-bottom:6px;">
      Editing inline. For full workspace, open the Editor page.
    </div>
    <textarea id="editor-text-dashboard">${data.content || ""}</textarea>
    <div style="margin-top:6px;">
      <button class="btn btn-primary" id="dash-save-file">Save</button>
    </div>
  `;

  document.getElementById("dash-save-file").onclick = async () => {
    const content = document.getElementById("editor-text-dashboard").value;
    await fetch(`${API_BASE}/api/files/write`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ project, path, content })
    });
    alert("Saved.");
  };
};

// ---------- MAIN LOG HELPER ----------

function pushMainLog(title, events) {
  const container = document.getElementById("panel-main-view");
  if (!container) return;

  const lines = (events || []).map(e => {
    const cls = `log-line ${e.kind || "info"}`;
    return `<div class="${cls}">[${e.kind}] ${e.message}</div>`;
  }).join("");

  container.innerHTML = `
    <h2>${title}</h2>
    <div class="log-panel">
      ${lines}
    </div>
  `;
}

// ---------- PAGE-SPECIFIC LOGIC ----------

async function initEditorPage() {
  if (!document.body.classList.contains("layout-page")) return;
  if (!document.title.includes("Editor")) return;

  initThemeToggle();

  const projectInput = document.getElementById("editor-project");
  const pathInput = document.getElementById("editor-path");
  const loadBtn = document.getElementById("editor-load");
  const saveBtn = document.getElementById("editor-save");
  const textArea = document.getElementById("editor-text");

  loadBtn.onclick = async () => {
    const project = projectInput.value.trim();
    const path = pathInput.value.trim();
    if (!project || !path) return;
    const res = await fetch(`${API_BASE}/api/files/read?project=${encodeURIComponent(project)}&path=${encodeURIComponent(path)}`);
    const data = await res.json();
    textArea.value = data.content || "";
  };

  saveBtn.onclick = async () => {
    const project = projectInput.value.trim();
    const path = pathInput.value.trim();
    const content = textArea.value;
    if (!project || !path) return;
    await fetch(`${API_BASE}/api/files/write`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ project, path, content })
    });
    alert("Saved.");
  };
}

async function initCloudflarePage() {
  if (!document.body.classList.contains("layout-page")) return;
  if (!document.title.includes("Cloudflare")) return;

  initThemeToggle();

  const projectInput = document.getElementById("cf-project");
  const logPanel = document.getElementById("cf-log");

  function logEvents(title, events) {
    logPanel.innerHTML = `<div class="small">${title}</div>` +
      (events || []).map(e => `<div class="log-line ${e.kind}">[${e.kind}] ${e.message}</div>`).join("");
  }

  async function call(endpoint) {
    const project = projectInput.value.trim();
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ project })
    });
    return res.json();
  }

  document.getElementById("cf-deploy-worker").onclick = async () => {
    const data = await call("/api/cloudflare/deploy_worker");
    logEvents("Deploy Worker", data.events);
  };

  document.getElementById("cf-deploy-pages").onclick = async () => {
    const data = await call("/api/cloudflare/deploy_pages");
    logEvents("Deploy Pages", data.events);
  };

  document.getElementById("cf-create-d1").onclick = async () => {
    const data = await call("/api/cloudflare/create_d1");
    logEvents("Create D1", data.events);
  };

  document.getElementById("cf-create-r2").onclick = async () => {
    const data = await call("/api/cloudflare/create_r2");
    logEvents("Create R2", data.events);
  };

  document.getElementById("cf-create-kv").onclick = async () => {
    const data = await call("/api/cloudflare/create_kv");
    logEvents("Create KV", data.events);
  };

  document.getElementById("cf-create-queue").onclick = async () => {
    const data = await call("/api/cloudflare/create_queue");
    logEvents("Create Queue", data.events);
  };
}

async function initCapabilitiesPage() {
  if (!document.body.classList.contains("layout-page")) return;
  if (!document.title.includes("Capabilities")) return;

  initThemeToggle();

  const container = document.getElementById("capabilities-list");
  const res = await fetch(`${API_BASE}/api/capabilities`);
  const data = await res.json();
  const caps = data.capabilities || [];

  container.innerHTML = caps
    .map(c => `<div><strong>${c.name}</strong><br/><span class="small">${c.description}</span></div>`)
    .join("<hr style='border:none;border-top:1px solid var(--border);margin:6px 0;' />");
}

async function initPluginsPage() {
  if (!document.body.classList.contains("layout-page")) return;
  if (!document.title.includes("Plugins")) return;

  initThemeToggle();

  const container = document.getElementById("plugins-list");
  const res = await fetch(`${API_BASE}/api/plugins`);
  const data = await res.json();
  const plugins = data.plugins || [];

  container.innerHTML = plugins
    .map(p => `<div><strong>${p.name}</strong> <span class="small">(${p.kind})</span></div>`)
    .join("");
}

async function initLogsPage() {
  if (!document.body.classList.contains("layout-page")) return;
  if (!document.title.includes("Logs")) return;

  initThemeToggle();

  const pre = document.getElementById("logs-output");
  const res = await fetch(`${API_BASE}/api/logs`);
  const data = await res.json();
  const lines = data.lines || [];
  pre.textContent = lines.join("\n");
}

// ---------- BOOTSTRAP ----------

window.addEventListener("DOMContentLoaded", async () => {
  await initDashboard();
  await initEditorPage();
  await initCloudflarePage();
  await initCapabilitiesPage();
  await initPluginsPage();
  await initLogsPage();
});
