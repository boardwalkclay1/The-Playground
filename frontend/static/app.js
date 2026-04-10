// static/app.js
// Unified frontend for Generator, AI Assistant, Project Manager, File Tree, Editor, Terminal, Microcontroller, Preview, Logs, Errors

// =====================================================
// GLOBAL STATE
// =====================================================
let currentProjectName = null;
let currentFilePath = null;

// DOM shortcuts
const $ = (id) => document.getElementById(id);

// =====================================================
// ON LOAD
// =====================================================
document.addEventListener("DOMContentLoaded", () => {
  initUI();
  bindPanels();
  refreshProjects();
  refreshCapabilities();
});

// =====================================================
// INIT UI
// =====================================================
function initUI() {
  // Ensure required DOM nodes exist
  const required = [
    "generator-input",
    "generator-run",
    "assistant-input",
    "assistant-run",
    "assistant-output",
    "terminal-input",
    "terminal-run",
    "terminal-output",
    "mcu-input",
    "mcu-run",
    "mcu-output",
    "panel-preview",
    "panel-main-view",
    "panel-projects",
    "panel-filetree",
    "panel-capabilities",
    "logs-output",
    "errors-output",
  ];
  required.forEach((id) => {
    if (!$(id)) {
      console.warn(`Missing DOM element: ${id}`);
    }
  });
}

// =====================================================
// FETCH HELPERS
// =====================================================
async function apiGet(path) {
  try {
    const res = await fetch(path, { method: "GET" });
    return await res.json();
  } catch (err) {
    console.error("GET", path, err);
    return { success: false, error: err.message };
  }
}

async function apiPost(path, body) {
  try {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    return await res.json();
  } catch (err) {
    console.error("POST", path, err);
    return { success: false, error: err.message };
  }
}

// =====================================================
// BIND PANELS
// =====================================================
function bindPanels() {
  bindGenerator();
  bindAssistant();
  bindTerminal();
  bindMicrocontroller();
  bindProjectManagerUI();
  // File tree and editor are dynamic; initial render below
  renderFileTreePlaceholder();
  renderEditorPlaceholder();
}

// =====================================================
// GENERATOR
// =====================================================
function bindGenerator() {
  const runBtn = $("generator-run");
  if (!runBtn) return;
  runBtn.addEventListener("click", async () => {
    const prompt = ($("generator-input") || {}).value || "";
    const logsEl = $("logs-output");
    const errorsEl = $("errors-output");
    if (!prompt.trim()) {
      if (errorsEl) errorsEl.textContent = "Generator prompt is empty.";
      return;
    }

    const projectName = `project-${Date.now()}`;
    currentProjectName = projectName;
    if (logsEl) logsEl.textContent = `Starting generation for ${projectName}...\n`;
    if (errorsEl) errorsEl.textContent = "";

    const res = await apiPost("/api/generator/run", {
      prompt,
      project_name: projectName,
      app_type: "generic",
    });

    if (res.logs && Array.isArray(res.logs)) {
      logsEl.textContent = res.logs.map((l) => `[${(l.level || "info").toUpperCase()}] ${l.message}`).join("\n");
    }

    if (res.errors && res.errors.length) {
      errorsEl.textContent = res.errors.join("\n");
    }

    if (res.success) {
      await refreshProjects();
      await refreshFileTree(projectName);
      loadPreview(projectName);
      showMainMessage(`Generated ${projectName}`);
    } else {
      if (errorsEl && res.error) errorsEl.textContent = res.error;
    }
  });
}

// =====================================================
// AI ASSISTANT
// =====================================================
function bindAssistant() {
  const runBtn = $("assistant-run");
  if (!runBtn) return;
  runBtn.addEventListener("click", async () => {
    const input = ($("assistant-input") || {}).value || "";
    const out = $("assistant-output");
    if (!input.trim()) {
      if (out) out.textContent = "Assistant prompt is empty.";
      return;
    }
    if (!currentProjectName) {
      if (out) out.textContent = "No project selected.";
      return;
    }

    if (out) out.textContent = "Assistant running...\n";
    const res = await apiPost("/api/assistant/run", {
      prompt: input,
      project_name: currentProjectName,
    });

    if (out) out.textContent = JSON.stringify(res, null, 2);
    // refresh file tree/editor if assistant modified files
    await refreshFileTree(currentProjectName);
    if (currentFilePath) {
      // if current file exists, reload it
      await openFile(currentFilePath);
    }
  });
}

// =====================================================
// TERMINAL
// =====================================================
function bindTerminal() {
  const runBtn = $("terminal-run");
  if (!runBtn) return;
  runBtn.addEventListener("click", async () => {
    const cmd = ($("terminal-input") || {}).value || "";
    const out = $("terminal-output");
    if (!cmd.trim()) {
      if (out) out.textContent = "Command is empty.";
      return;
    }
    if (!currentProjectName) {
      if (out) out.textContent = "No project selected.";
      return;
    }

    if (out) out.textContent = `Running: ${cmd}\n`;
    // Use terminal endpoint if available; fallback to assistant run
    const res = await apiPost("/api/terminal/run", {
      project_name: currentProjectName,
      command: cmd,
    });

    if (out) out.textContent = JSON.stringify(res, null, 2);
    // update logs/errors panels if present
    if (res.logs && Array.isArray(res.logs)) {
      $("logs-output").textContent = res.logs.map((l) => `[${l.level}] ${l.message}`).join("\n");
    }
    if (res.error) {
      $("errors-output").textContent = res.error;
    }
  });
}

// =====================================================
// MICROCONTROLLER PANEL
// =====================================================
function bindMicrocontroller() {
  const runBtn = $("mcu-run");
  if (!runBtn) return;
  runBtn.addEventListener("click", async () => {
    const prompt = ($("mcu-input") || {}).value || "";
    const out = $("mcu-output");
    if (!prompt.trim()) {
      if (out) out.textContent = "Microcontroller prompt is empty.";
      return;
    }

    if (out) out.textContent = "Generating firmware (AI)...\n";

    const res = await apiPost("/api/microcontroller/generate", {
      project_name: currentProjectName || "mcu-sandbox",
      prompt,
    });

    if (out) out.textContent = JSON.stringify(res, null, 2);
    // refresh file tree if sandbox used
    if (currentProjectName === (res.project || "mcu-sandbox")) {
      await refreshFileTree(currentProjectName);
    }
  });
}

// =====================================================
// PROJECT MANAGER
// =====================================================
function bindProjectManagerUI() {
  const panel = $("panel-projects");
  if (!panel) return;
  panel.innerHTML = `
    <h3>Projects</h3>
    <div class="pm-controls">
      <input id="pm-new-name" placeholder="New project name" />
      <button id="pm-create" class="btn">Create</button>
    </div>
    <div id="pm-list" class="pm-list"></div>
  `;
  $("pm-create").addEventListener("click", async () => {
    const name = ($("pm-new-name") || {}).value || "";
    if (!name.trim()) return alert("Enter a project name");
    const res = await apiPost("/api/projects/create", { name });
    if (res.success) {
      $("pm-new-name").value = "";
      await refreshProjects();
    } else {
      alert(res.error || "Create failed");
    }
  });
}

async function refreshProjects() {
  const listEl = $("pm-list");
  if (!listEl) return;
  listEl.textContent = "Loading...";
  const res = await apiGet("/api/projects");
  if (!res.success) {
    listEl.textContent = "Failed to load projects";
    return;
  }
  listEl.innerHTML = "";
  res.projects.forEach((p) => {
    const row = document.createElement("div");
    row.className = "pm-row";
    row.innerHTML = `
      <span class="pm-name">${p}</span>
      <button class="btn pm-open">Open</button>
      <button class="btn pm-dup">Duplicate</button>
      <button class="btn pm-del">Delete</button>
    `;
    row.querySelector(".pm-open").addEventListener("click", async () => {
      currentProjectName = p;
      await refreshFileTree(p);
      loadPreview(p);
      showMainMessage(`Opened ${p}`);
    });
    row.querySelector(".pm-dup").addEventListener("click", async () => {
      const resDup = await apiPost("/api/projects/duplicate", { name: p });
      if (resDup.success) await refreshProjects();
      else alert(resDup.error || "Duplicate failed");
    });
    row.querySelector(".pm-del").addEventListener("click", async () => {
      if (!confirm(`Delete project ${p}?`)) return;
      const resDel = await apiPost("/api/projects/delete", { name: p });
      if (resDel.success) {
        if (currentProjectName === p) {
          currentProjectName = null;
          renderFileTreePlaceholder();
          renderEditorPlaceholder();
        }
        await refreshProjects();
      } else {
        alert(resDel.error || "Delete failed");
      }
    });
    listEl.appendChild(row);
  });
}

// =====================================================
// FILE TREE + EDITOR
// =====================================================
function renderFileTreePlaceholder() {
  const panel = $("panel-filetree");
  if (!panel) return;
  panel.innerHTML = `<h3>File Tree</h3><p>No project selected</p>`;
}

function renderEditorPlaceholder() {
  const main = $("panel-main-view");
  if (!main) return;
  main.innerHTML = `<h3>Editor</h3><p>Select a file to edit</p>`;
}

async function refreshFileTree(projectName = currentProjectName) {
  const panel = $("panel-filetree");
  if (!panel) return;
  if (!projectName) {
    renderFileTreePlaceholder();
    return;
  }
  panel.innerHTML = `<h3>File Tree</h3><p>Loading...</p>`;
  const res = await apiGet(`/api/files/tree/${encodeURIComponent(projectName)}`);
  if (!res.success) {
    panel.innerHTML = `<h3>File Tree</h3><p>Failed to load</p>`;
    return;
  }

  const container = document.createElement("div");
  container.className = "filetree";

  function renderNodes(nodes) {
    const ul = document.createElement("ul");
    nodes.forEach((n) => {
      const li = document.createElement("li");
      li.className = `node node-${n.type}`;
      const label = document.createElement("span");
      label.textContent = n.name;
      label.dataset.path = n.path;
      label.className = "node-label";
      if (n.type === "file") {
        label.addEventListener("click", () => openFile(n.path));
      }
      li.appendChild(label);
      if (n.type === "dir" && Array.isArray(n.children)) {
        li.appendChild(renderNodes(n.children));
      }
      ul.appendChild(li);
    });
    return ul;
  }

  container.appendChild(renderNodes(res.tree));

  // file ops UI
  const ops = document.createElement("div");
  ops.className = "file-ops";
  ops.innerHTML = `
    <div class="ops-row">
      <input id="op-new-path" placeholder="path/to/newfile.txt" />
      <button id="op-create" class="btn">Create</button>
    </div>
    <div class="ops-row">
      <input id="op-delete-path" placeholder="path/to/delete" />
      <button id="op-delete" class="btn">Delete</button>
    </div>
    <div class="ops-row">
      <input id="op-move-src" placeholder="src/path" />
      <input id="op-move-dst" placeholder="dst/path" />
      <button id="op-move" class="btn">Move</button>
    </div>
  `;
  container.appendChild(ops);

  panel.innerHTML = `<h3>File Tree</h3>`;
  panel.appendChild(container);

  // ops handlers
  $("op-create").addEventListener("click", async () => {
    const path = ($("op-new-path") || {}).value || "";
    if (!path.trim()) return alert("Enter path");
    const res = await apiPost("/api/files/write", { project_name: projectName, path, content: "" });
    if (res.success) {
      await refreshFileTree(projectName);
    } else {
      alert(res.error || "Create failed");
    }
  });

  $("op-delete").addEventListener("click", async () => {
    const path = ($("op-delete-path") || {}).value || "";
    if (!path.trim()) return alert("Enter path");
    const res = await apiPost("/api/files/delete", { project_name: projectName, path });
    if (res.success) {
      if (currentFilePath === path) {
        currentFilePath = null;
        renderEditorPlaceholder();
      }
      await refreshFileTree(projectName);
    } else {
      alert(res.error || "Delete failed");
    }
  });

  $("op-move").addEventListener("click", async () => {
    const src = ($("op-move-src") || {}).value || "";
    const dst = ($("op-move-dst") || {}).value || "";
    if (!src.trim() || !dst.trim()) return alert("Enter src and dst");
    const res = await apiPost("/api/files/move", { project_name: projectName, src, dst });
    if (res.success) {
      if (currentFilePath === src) currentFilePath = dst;
      await refreshFileTree(projectName);
    } else {
      alert(res.error || "Move failed");
    }
  });
}

async function openFile(path) {
  if (!currentProjectName) return alert("No project selected");
  const main = $("panel-main-view");
  if (!main) return;
  main.innerHTML = `<h3>Editor</h3><p>Loading ${path}...</p>`;
  const res = await apiPost("/api/files/read", { project_name: currentProjectName, path });
  if (!res.success) {
    main.innerHTML = `<h3>Editor</h3><p>Failed to load file</p>`;
    return;
  }

  currentFilePath = path;

  const wrapper = document.createElement("div");
  wrapper.className = "editor";

  const title = document.createElement("div");
  title.className = "editor-title";
  title.textContent = `${currentProjectName} / ${path}`;

  const textarea = document.createElement("textarea");
  textarea.className = "editor-textarea";
  textarea.value = res.content || "";

  const controls = document.createElement("div");
  controls.className = "editor-controls";
  controls.innerHTML = `
    <button id="editor-save" class="btn btn-primary">Save</button>
    <button id="editor-revert" class="btn">Revert</button>
    <button id="editor-download" class="btn">Download</button>
  `;

  wrapper.appendChild(title);
  wrapper.appendChild(textarea);
  wrapper.appendChild(controls);

  main.innerHTML = "";
  main.appendChild(wrapper);

  $("editor-save").addEventListener("click", async () => {
    const content = textarea.value;
    const r = await apiPost("/api/files/write", { project_name: currentProjectName, path: currentFilePath, content });
    if (r.success) {
      showMainMessage("Saved.");
      await refreshFileTree(currentProjectName);
    } else {
      alert(r.error || "Save failed");
    }
  });

  $("editor-revert").addEventListener("click", async () => {
    await openFile(currentFilePath);
  });

  $("editor-download").addEventListener("click", () => {
    const blob = new Blob([textarea.value], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = currentFilePath.split("/").pop() || "file.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
  });
}

// =====================================================
// PREVIEW
// =====================================================
function loadPreview(projectName) {
  const panel = $("panel-preview");
  if (!panel) return;
  panel.innerHTML = `<h3>Preview</h3>`;
  const iframe = document.createElement("iframe");
  iframe.className = "preview-frame";
  iframe.src = `/preview/${encodeURIComponent(projectName)}`;
  iframe.style.width = "100%";
  iframe.style.height = "600px";
  iframe.addEventListener("error", () => {
    $("errors-output").textContent = "Preview failed to load.";
  });
  panel.appendChild(iframe);
}

// =====================================================
// CAPABILITIES PANEL
// =====================================================
function refreshCapabilities() {
  const panel = $("panel-capabilities");
  if (!panel) return;
  panel.innerHTML = `
    <h3>Capabilities</h3>
    <details open>
      <summary>Core Engines</summary>
      <ul>
        <li>App Generator Engine (generator/orchestrator)</li>
        <li>AI Assistant Engine (assistant.AIAgent)</li>
        <li>File Engine (files API: read/write/tree/move/delete)</li>
        <li>Project Manager (create/duplicate/delete/rename)</li>
        <li>Terminal Engine (terminal API or assistant fallback)</li>
        <li>Microcontroller Engine (generate/flash)</li>
        <li>Cloudflare Deploy (optional engine)</li>
      </ul>
    </details>
    <details>
      <summary>Planned Features</summary>
      <ul>
        <li>Syntax highlighting editor (Monaco/CodeMirror)</li>
        <li>Live logs streaming</li>
        <li>ESP toolchain integration (esptool, platformio)</li>
        <li>Cloudflare Workers/Pages deploy UI</li>
        <li>R2 / D1 / KV management</li>
      </ul>
    </details>
  `;
}

// =====================================================
// UTIL / UI HELPERS
// =====================================================
function showMainMessage(msg) {
  const main = $("panel-main-view");
  if (!main) return;
  const el = document.createElement("div");
  el.className = "main-message";
  el.textContent = msg;
  main.prepend(el);
  setTimeout(() => el.remove(), 3000);
}

// =====================================================
// EXPORTS for debugging (optional)
// =====================================================
window.Playground = {
  refreshProjects,
  refreshFileTree,
  openFile,
  loadPreview,
};
