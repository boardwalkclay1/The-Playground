// static/app.js
// NEW LAYOUT VERSION — MATCHES NEW index.html + new CSS

let currentProjectName = null;
let currentFilePath = null;

const API_BASE = "http://localhost:8000";
const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  bindSidebar();
  bindDockTabs();
  bindTerminal();
  bindAI();
  loadHomeScreen();
});

/* ---------------------------------------------------------
   SIDEBAR NAVIGATION → loads panels into #main-content
--------------------------------------------------------- */
function bindSidebar() {
  document.querySelectorAll(".pg-nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const panel = btn.dataset.panel;
      loadPanel(panel);
    });
  });
}

function loadPanel(panel) {
  switch (panel) {
    case "projects":
      renderProjectsPanel();
      break;
    case "filetree":
      renderFileTreePanel();
      break;
    case "generator":
      renderGeneratorPanel();
      break;
    case "microcontroller":
      renderMCUPanel();
      break;
    case "cloudflare":
      $("main-content").innerHTML = `<h2>Cloudflare</h2><p class="muted">Coming soon.</p>`;
      break;
    case "capabilities":
      renderCapabilitiesPanel();
      break;
    case "settings":
      $("main-content").innerHTML = `<h2>Settings</h2><p class="muted">Coming soon.</p>`;
      break;
    default:
      loadHomeScreen();
  }
}

function loadHomeScreen() {
  $("main-content").innerHTML = `
    <h2>Welcome</h2>
    <p class="muted">Choose a tool from the left sidebar.</p>
  `;
}

/* ---------------------------------------------------------
   DOCK TABS (Terminal / Errors / AI)
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

    if (!cmd) {
      out.textContent = "Command is empty.";
      return;
    }
    if (!currentProjectName) {
      out.textContent = "No project selected.";
      return;
    }

    out.textContent = `Running: ${cmd}\n`;

    const res = await apiPost("/api/terminal/run", {
      project_name: currentProjectName,
      command: cmd,
    });

    out.textContent = JSON.stringify(res, null, 2);

    if (res.error) $("dock-errors").textContent = res.error;
  });

  $("terminal-clear").addEventListener("click", () => {
    $("terminal-output").textContent = "";
  });
}

/* ---------------------------------------------------------
   AI ASSISTANT (dock panel)
--------------------------------------------------------- */
function bindAI() {
  $("ai-send").addEventListener("click", async () => {
    const input = $("ai-input").value.trim();
    const out = $("ai-output");

    if (!input) {
      out.textContent = "Assistant prompt is empty.";
      return;
    }
    if (!currentProjectName) {
      out.textContent = "No project selected.";
      return;
    }

    out.textContent = "Assistant running...\n";

    const res = await apiPost("/api/assistant/run", {
      prompt: input,
      project_name: currentProjectName,
    });

    out.textContent = JSON.stringify(res, null, 2);

    if (currentFilePath) openFile(currentFilePath);
  });
}

/* ---------------------------------------------------------
   GENERATOR PANEL
--------------------------------------------------------- */
function renderGeneratorPanel() {
  $("main-content").innerHTML = `
    <h2>App Generator</h2>
    <textarea id="generator-input" placeholder="Describe the app..."></textarea>
    <button id="generator-run" class="pg-btn-primary" style="margin-top:10px;">Generate</button>
  `;

  $("generator-run").addEventListener("click", async () => {
    const prompt = $("generator-input").value.trim();
    if (!prompt) return alert("Prompt empty");

    const projectName = `project-${Date.now()}`;
    currentProjectName = projectName;

    const res = await apiPost("/api/generator/run", {
      prompt,
      project_name: projectName,
      app_type: "generic",
    });

    if (res.success) {
      renderProjectsPanel();
      renderFileTreePanel();
      loadPreview(projectName);
      showMessage("Generated " + projectName);
    } else {
      $("dock-errors").textContent = res.error || "Generation failed.";
    }
  });
}

/* ---------------------------------------------------------
   PROJECTS PANEL
--------------------------------------------------------- */
function renderProjectsPanel() {
  $("main-content").innerHTML = `
    <h2>Projects</h2>
    <input id="pm-new-name" placeholder="New project name" />
    <button id="pm-create" class="pg-btn-primary" style="margin-top:8px;">Create</button>
    <div id="pm-list" style="margin-top:12px;"></div>
  `;

  $("pm-create").addEventListener("click", async () => {
    const name = $("pm-new-name").value.trim();
    if (!name) return;

    const res = await apiPost("/api/projects/create", { name });
    if (res.success) renderProjectsPanel();
  });

  loadProjects();
}

async function loadProjects() {
  const list = $("pm-list");
  list.textContent = "Loading...";

  const res = await apiGet("/api/projects");
  if (!res.success) {
    list.textContent = "Failed to load projects";
    return;
  }

  list.innerHTML = "";
  res.projects.forEach((p) => {
    const row = document.createElement("div");
    row.style.marginBottom = "6px";
    row.innerHTML = `
      <strong>${p}</strong>
      <button class="pg-btn pm-open">Open</button>
      <button class="pg-btn pm-del">Delete</button>
    `;

    row.querySelector(".pm-open").addEventListener("click", async () => {
      currentProjectName = p;
      renderFileTreePanel();
      loadPreview(p);
      showMessage(`Opened ${p}`);
    });

    row.querySelector(".pm-del").addEventListener("click", async () => {
      if (!confirm(`Delete ${p}?`)) return;
      const r = await apiPost("/api/projects/delete", { name: p });
      if (r.success) renderProjectsPanel();
    });

    list.appendChild(row);
  });
}

/* ---------------------------------------------------------
   FILE TREE PANEL
--------------------------------------------------------- */
function renderFileTreePanel() {
  if (!currentProjectName) {
    $("main-content").innerHTML = `<h2>File Tree</h2><p class="muted">No project selected.</p>`;
    return;
  }

  $("main-content").innerHTML = `<h2>File Tree</h2><p>Loading...</p>`;
  loadFileTree();
}

async function loadFileTree() {
  const res = await apiGet(`/api/files/tree/${currentProjectName}`);
  if (!res.success) {
    $("main-content").innerHTML = `<h2>File Tree</h2><p>Failed to load.</p>`;
    return;
  }

  const container = document.createElement("div");

  function renderNodes(nodes) {
    const ul = document.createElement("ul");
    nodes.forEach((n) => {
      const li = document.createElement("li");
      li.textContent = n.name;
      li.style.cursor = "pointer";

      if (n.type === "file") {
        li.addEventListener("click", () => openFile(n.path));
      }

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
    $("main-content").innerHTML = `<h2>Editor</h2><p>Failed to load file.</p>`;
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

    if (r.success) showMessage("Saved.");
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
   CAPABILITIES
--------------------------------------------------------- */
function renderCapabilitiesPanel() {
  $("main-content").innerHTML = `
    <h2>Capabilities</h2>
    <ul>
      <li>App Generator</li>
      <li>AI Assistant</li>
      <li>File Engine</li>
      <li>Terminal Engine</li>
      <li>Microcontroller Engine</li>
      <li>Breadboard Lab</li>
    </ul>
  `;
}

/* ---------------------------------------------------------
   MCU PANEL
--------------------------------------------------------- */
function renderMCUPanel() {
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
function showMessage(msg) {
  const el = document.createElement("div");
  el.textContent = msg;
  el.style.padding = "6px";
  el.style.marginTop = "6px";
  el.style.background = "var(--accent-soft)";
  el.style.borderRadius = "6px";
  $("main-content").prepend(el);
  setTimeout(() => el.remove(), 3000);
}
