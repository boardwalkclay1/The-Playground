// static/app.js — FINAL REWRITE WITH AI DRAWER + FLOAT BUTTON

let currentProjectName = null;
let currentFilePath = null;

// Auto-detect backend
function detectBackend() {
  const saved = localStorage.getItem("backend_url");
  if (saved) return saved;
  if (window.location.hostname !== "localhost") return window.location.origin;
  return "http://localhost:8000";
}

let API_BASE = detectBackend();
const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  bindSidebar();
  bindDockTabs();
  bindTerminal();
  bindAI();
  bindAIFloatButton();
  loadHome();
});

/* ---------------------------------------------------------
   SIDEBAR
--------------------------------------------------------- */
function bindSidebar() {
  document.querySelectorAll(".pg-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => loadPanel(btn.dataset.panel));
  });
}

function loadPanel(panel) {
  switch (panel) {
    case "projects": renderProjects(); break;
    case "filetree": renderFileTree(); break;
    case "generator": renderGenerator(); break;
    case "microcontroller": renderMCU(); break;
    case "cloudflare": loadPage("cloudflare.html"); break;
    case "capabilities": loadPage("capabilities.html"); break;
    case "settings": renderSettings(); break;
    default: loadHome();
  }
}

function loadPage(page) {
  $("main-content").innerHTML = `<iframe src="${page}" style="width:100%;height:80vh;border:0;"></iframe>`;
}

function loadHome() {
  $("main-content").innerHTML = `
    <h2>Welcome</h2>
    <p class="muted">Choose a tool from the left sidebar.</p>
  `;
}

/* ---------------------------------------------------------
   DOCK TABS (Terminal / Logs / Errors)
--------------------------------------------------------- */
function bindDockTabs() {
  const tabs = document.querySelectorAll(".pg-dock-tab");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");

      const target = tab.dataset.dock;

      document.querySelectorAll(".pg-dock-panel").forEach((p) => {
        p.classList.add("hidden");
      });

      $(`dock-${target}`).classList.remove("hidden");
    });
  });
}

/* ---------------------------------------------------------
   TERMINAL
--------------------------------------------------------- */
function bindTerminal() {
  $("terminal-run").addEventListener("click", async () => {
    const cmd = $("terminal-input").value.trim();
    const out = $("terminal-output");

    if (!cmd) return out.textContent = "Command empty.";
    if (!currentProjectName) return out.textContent = "No project selected.";

    out.textContent = `Running: ${cmd}\n`;

    const res = await apiPost("/api/terminal/run", {
      project_name: currentProjectName,
      command: cmd,
    });

    out.textContent = JSON.stringify(res, null, 2);

    if (res.error) $("errors-output").textContent = res.error;
  });

  $("terminal-clear").addEventListener("click", () => {
    $("terminal-output").textContent = "";
  });
}

/* ---------------------------------------------------------
   AI ASSISTANT (Drawer)
--------------------------------------------------------- */
function bindAI() {
  $("ai-send").addEventListener("click", async () => {
    const input = $("ai-input").value.trim();
    const out = $("ai-output");

    if (!input) return out.textContent = "Prompt empty.";
    if (!currentProjectName) return out.textContent = "No project selected.";

    out.textContent = "Running...\n";

    const res = await apiPost("/api/assistant/run", {
      prompt: input,
      project_name: currentProjectName,
    });

    out.textContent = JSON.stringify(res, null, 2);

    if (currentFilePath) openFile(currentFilePath);
  });
}

/* ---------------------------------------------------------
   FLOATING AI BUTTON
--------------------------------------------------------- */
function bindAIFloatButton() {
  const btn = document.createElement("button");
  btn.id = "ai-float-btn";
  btn.textContent = "AI";
  document.body.appendChild(btn);

  btn.addEventListener("click", () => {
    document.body.classList.toggle("ai-open");
  });
}

/* ---------------------------------------------------------
   GENERATOR
--------------------------------------------------------- */
function renderGenerator() {
  $("main-content").innerHTML = `
    <h2>App Generator</h2>
    <textarea id="generator-input" placeholder="Describe the app..."></textarea>
    <button id="generator-run" class="pg-btn-primary" style="margin-top:10px;">Generate</button>
  `;

  $("generator-run").addEventListener("click", async () => {
    const prompt = $("generator-input").value.trim();
    if (!prompt) return;

    const projectName = `project-${Date.now()}`;
    currentProjectName = projectName;

    const res = await apiPost("/api/generator/run", {
      prompt,
      project_name: projectName,
      app_type: "generic",
    });

    if (res.success) {
      renderProjects();
      renderFileTree();
      loadPreview(projectName);
      message("Generated " + projectName);
    } else {
      $("errors-output").textContent = res.error || "Generation failed.";
    }
  });
}

/* ---------------------------------------------------------
   PROJECTS
--------------------------------------------------------- */
function renderProjects() {
  $("main-content").innerHTML = `
    <h2>Projects</h2>
    <input id="pm-new" placeholder="New project name">
    <button id="pm-create" class="pg-btn-primary" style="margin-top:8px;">Create</button>
    <div id="pm-list" style="margin-top:12px;"></div>
  `;

  $("pm-create").addEventListener("click", async () => {
    const name = $("pm-new").value.trim();
    if (!name) return;

    const res = await apiPost("/api/projects/create", { name });
    if (res.success) renderProjects();
  });

  loadProjects();
}

async function loadProjects() {
  const list = $("pm-list");
  list.textContent = "Loading...";

  const res = await apiGet("/api/projects");
  if (!res.success) return list.textContent = "Failed to load.";

  list.innerHTML = "";
  res.projects.forEach((p) => {
    const row = document.createElement("div");
    row.style.marginBottom = "6px";
    row.innerHTML = `
      <strong>${p}</strong>
      <button class="pg-btn pm-open">Open</button>
      <button class="pg-btn pm-del">Delete</button>
    `;

    row.querySelector(".pm-open").addEventListener("click", () => {
      currentProjectName = p;
      renderFileTree();
      loadPreview(p);
      message(`Opened ${p}`);
    });

    row.querySelector(".pm-del").addEventListener("click", async () => {
      if (!confirm(`Delete ${p}?`)) return;
      const r = await apiPost("/api/projects/delete", { name: p });
      if (r.success) renderProjects();
    });

    list.appendChild(row);
  });
}

/* ---------------------------------------------------------
   FILE TREE
--------------------------------------------------------- */
function renderFileTree() {
  if (!currentProjectName) {
    $("main-content").innerHTML = `<h2>File Tree</h2><p class="muted">No project selected.</p>`;
    return;
  }

  $("main-content").innerHTML = `<h2>File Tree</h2><p>Loading...</p>`;
  loadTree();
}

async function loadTree() {
  const res = await apiGet(`/api/files/tree/${currentProjectName}`);
  if (!res.success) {
    $("main-content").innerHTML = `<h2>File Tree</h2><p>Failed.</p>`;
    return;
  }

  const container = document.createElement("div");

  function renderNodes(nodes) {
    const ul = document.createElement("ul");
    nodes.forEach((n) => {
      const li = document.createElement("li");
      li.textContent = n.name;
      li.style.cursor = "pointer";

      if (n.type === "file") li.addEventListener("click", () => openFile(n.path));
      if (n.children) li.appendChild(renderNodes(n.children));

      ul.appendChild(li);
    });
    return ul;
  }

  container.appendChild(renderNodes(res.tree));

  $("main-content").innerHTML = `<h2>File Tree</h2>`;
  $("main-content").appendChild(container);
}

/* ---------------------------------------------------------
   EDITOR
--------------------------------------------------------- */
async function openFile(path) {
  const res = await apiPost("/api/files/read", {
    project_name: currentProjectName,
    path,
  });

  if (!res.success) {
    $("main-content").innerHTML = `<h2>Editor</h2><p>Failed to load.</p>`;
    return;
  }

  currentFilePath = path;

  $("main-content").innerHTML = `
    <h2>Editor</h2>
    <div><strong>${path}</strong></div>
    <textarea id="editor-text" style="width:100%;height:400px;margin-top:10px;">${res.content || ""}</textarea>
    <button id="editor-save" class="pg-btn-primary" style="margin-top:10px;">Save</button>
  `;

  $("editor-save").addEventListener("click", async () => {
    const r = await apiPost("/api/files/write", {
      project_name: currentProjectName,
      path,
      content: $("editor-text").value,
    });

    if (r.success) message("Saved.");
  });
}

/* ---------------------------------------------------------
   PREVIEW
--------------------------------------------------------- */
function loadPreview(projectName) {
  $("main-content").innerHTML = `
    <h2>Preview</h2>
    <iframe class="preview-frame" src="${API_BASE}/preview/${projectName}"></iframe>
  `;
}

/* ---------------------------------------------------------
   MCU
--------------------------------------------------------- */
function renderMCU() {
  $("main-content").innerHTML = `
    <h2>Microcontroller Builder</h2>
    <textarea id="mcu-input" placeholder="Describe firmware..."></textarea>
    <button id="mcu-run" class="pg-btn-primary" style="margin-top:10px;">Generate</button>
    <pre id="mcu-output" style="margin-top:10px;"></pre>
  `;

  $("mcu-run").addEventListener("click", async () => {
    const prompt = $("mcu-input").value.trim();
    if (!prompt) return;

    const res = await apiPost("/mcu/generate", {
      project_name: "mcu-sandbox",
      prompt,
      merge_strategy: "overwrite",
    });

    $("mcu-output").textContent = JSON.stringify(res, null, 2);
  });
}

/* ---------------------------------------------------------
   SETTINGS
--------------------------------------------------------- */
function renderSettings() {
  $("main-content").innerHTML = `
    <h2>Settings</h2>
    <input id="backend-url" placeholder="Backend URL" style="width:260px;">
    <button id="backend-save" class="pg-btn-primary" style="margin-left:8px;">Save</button>
  `;

  $("backend-save").addEventListener("click", () => {
    const url = $("backend-url").value.trim();
    if (!url) return;

    localStorage.setItem("backend_url", url);
    API_BASE = url;

    alert("Backend updated. Reloading...");
    location.reload();
  });
}

/* ---------------------------------------------------------
   API HELPERS
--------------------------------------------------------- */
async function apiGet(path) {
  try {
    const res = await fetch(API_BASE + path);
    return await res.json();
  } catch (err) {
    return { success: false, error: err.message };
  }
}

async function apiPost(path, body) {
  try {
    const res = await fetch(API_BASE + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return await res.json();
  } catch (err) {
    return { success: false, error: err.message };
  }
}

/* ---------------------------------------------------------
   UI MESSAGE
--------------------------------------------------------- */
function message(msg) {
  const el = document.createElement("div");
  el.textContent = msg;
  el.style.padding = "6px";
  el.style.marginTop = "6px";
  el.style.background = "var(--accent-soft)";
  el.style.borderRadius = "6px";
  $("main-content").prepend(el);
  setTimeout(() => el.remove(), 3000);
}
