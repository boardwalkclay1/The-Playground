// static/app.js
// Unified frontend for Generator, AI Assistant, Project Manager, File Tree, Editor, Terminal, Microcontroller, Preview, Logs, Errors

let currentProjectName = null;
let currentFilePath = null;

const API_BASE = "http://localhost:8000";   // <— FIXED: backend lives here
const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", () => {
  initUI();
  bindPanels();
  refreshProjects();
  refreshCapabilities();
});

/* ---------------- Helpers ---------------- */
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

/* ---------------- Init ---------------- */
function initUI() {
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
    if (!$(id)) console.warn("Missing DOM element:", id);
  });
}

/* ---------------- Bind Panels ---------------- */
function bindPanels() {
  bindGenerator();
  bindAssistant();
  bindTerminal();
  bindMicrocontroller();
  bindProjectManagerUI();
  renderFileTreePlaceholder();
  renderEditorPlaceholder();
}

/* ---------------- Generator ---------------- */
function bindGenerator() {
  const runBtn = $("generator-run");
  if (!runBtn) return;

  runBtn.addEventListener("click", async () => {
    const prompt = $("generator-input").value.trim();
    const logsEl = $("logs-output");
    const errorsEl = $("errors-output");

    if (!prompt) {
      errorsEl.textContent = "Generator prompt is empty.";
      return;
    }

    const projectName = `project-${Date.now()}`;
    currentProjectName = projectName;

    logsEl.textContent = `Starting generation for ${projectName}...\n`;
    errorsEl.textContent = "";

    const res = await apiPost("/api/generator/run", {
      prompt,
      project_name: projectName,
      app_type: "generic",
    });

    if (res.logs) {
      logsEl.textContent = res.logs
        .map((l) => `[${(l.level || "info").toUpperCase()}] ${l.message}`)
        .join("\n");
    }

    if (res.errors?.length) {
      errorsEl.textContent = res.errors.join("\n");
    }

    if (res.success) {
      await refreshProjects();
      await refreshFileTree(projectName);
      loadPreview(projectName);
      showMainMessage(`Generated ${projectName}`);
    } else {
      errorsEl.textContent = res.error || "Generation failed.";
    }
  });
}

/* ---------------- Assistant ---------------- */
function bindAssistant() {
  const runBtn = $("assistant-run");
  if (!runBtn) return;

  runBtn.addEventListener("click", async () => {
    const input = $("assistant-input").value.trim();
    const out = $("assistant-output");

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

    await refreshFileTree(currentProjectName);
    if (currentFilePath) await openFile(currentFilePath);
  });
}

/* ---------------- Terminal ---------------- */
function bindTerminal() {
  const runBtn = $("terminal-run");
  if (!runBtn) return;

  runBtn.addEventListener("click", async () => {
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

    if (res.logs) {
      $("logs-output").textContent = res.logs
        .map((l) => `[${l.level}] ${l.message}`)
        .join("\n");
    }
    if (res.error) $("errors-output").textContent = res.error;
  });
}

/* ---------------- MCU PANEL ---------------- */
function bindMicrocontroller() {
  const panel = $("panel-microcontroller");
  if (!panel) return;

  panel.innerHTML = `
    <h3>Microcontroller Builder</h3>

    <textarea id="mcu-input" placeholder="Describe the ESP32 firmware you want..."></textarea>

    <div style="margin-top:8px;">
      <input id="mcu-project" placeholder="Project name (default: mcu-sandbox)" />
    </div>

    <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap;">
      <select id="mcu-board" class="btn small">
        <option value="">Board: auto</option>
      </select>

      <select id="mcu-template" class="btn small">
        <option value="">Template: none</option>
      </select>

      <select id="mcu-example" class="btn small">
        <option value="">Example: ESP32 pack</option>
        <option value="esp32-wifi-scan">WiFi Scan</option>
        <option value="esp32-wifi-connect">WiFi Connect</option>
        <option value="esp32-ble-uart">BLE UART</option>
      </select>
    </div>

    <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
      <button id="mcu-run" class="btn">Generate Firmware</button>
      <button id="mcu-flash" class="btn">Flash (stub)</button>
      <button id="mcu-open-lab" class="btn">Open MCU Lab</button>
    </div>

    <pre id="mcu-output"></pre>
  `;

  loadMCUBoards();
  loadMCUTemplates();

  $("mcu-run").addEventListener("click", async () => {
    const prompt = $("mcu-input").value.trim();
    const out = $("mcu-output");

    if (!prompt) {
      out.textContent = "Microcontroller prompt is empty.";
      return;
    }

    const project = $("mcu-project").value.trim() || "mcu-sandbox";
    const board = $("mcu-board").value || null;
    const template = $("mcu-template").value || null;
    const example = $("mcu-example").value || null;

    out.textContent = "Generating firmware...";

    const res = await apiPost("/mcu/generate", {
      project_name: project,
      prompt,
      board_id: board,
      template_id: template || example || null,
      merge_strategy: "overwrite",
    });

    out.textContent = JSON.stringify(res, null, 2);

    if (currentProjectName === project) await refreshFileTree(project);
  });

  $("mcu-flash").addEventListener("click", async () => {
    const project = $("mcu-project").value.trim() || "mcu-sandbox";
    const out = $("mcu-output");

    out.textContent = "Flashing (stub)...";

    const res = await apiPost("/mcu/flash", { project_name: project });
    out.textContent = JSON.stringify(res, null, 2);
  });

  $("mcu-open-lab").addEventListener("click", () => {
    window.open("/static/microcontroller-lab.html", "_blank");
  });
}

async function loadMCUBoards() {
  const res = await apiGet("/mcu/boards");
  const sel = $("mcu-board");
  if (!res.boards) return;
  res.boards.forEach((b) => {
    const opt = document.createElement("option");
    opt.value = b.id;
    opt.textContent = b.name;
    sel.appendChild(opt);
  });
}

async function loadMCUTemplates() {
  const res = await apiGet("/mcu/templates");
  const sel = $("mcu-template");
  if (!res.templates) return;
  res.templates.forEach((t) => {
    const opt = document.createElement("option");
    opt.value = t.id;
    opt.textContent = t.name;
    sel.appendChild(opt);
  });
}

/* ---------------- Project Manager ---------------- */
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
    const name = $("pm-new-name").value.trim();
    if (!name) return alert("Enter a project name");

    const res = await apiPost("/api/projects/create", { name });
    if (res.success) {
      $("pm-new-name").value = "";
      await refreshProjects();
    } else alert(res.error || "Create failed");
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
      const r = await apiPost("/api/projects/duplicate", { name: p });
      if (r.success) refreshProjects();
      else alert(r.error || "Duplicate failed");
    });

    row.querySelector(".pm-del").addEventListener("click", async () => {
      if (!confirm(`Delete project ${p}?`)) return;
      const r = await apiPost("/api/projects/delete", { name: p });
      if (r.success) {
        if (currentProjectName === p) {
          currentProjectName = null;
          renderFileTreePlaceholder();
          renderEditorPlaceholder();
        }
        refreshProjects();
      } else alert(r.error || "Delete failed");
    });

    listEl.appendChild(row);
  });
}

/* ---------------- File Tree + Editor ---------------- */
function renderFileTreePlaceholder() {
  $("panel-filetree").innerHTML = `<h3>File Tree</h3><p>No project selected</p>`;
}

function renderEditorPlaceholder() {
  $("panel-main-view").innerHTML = `<h3>Editor</h3><p>Select a file to edit</p>`;
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

  panel.innerHTML = `<h3>File Tree</h3>`;
  panel.appendChild(container);
}

async function openFile(path) {
  if (!currentProjectName) return alert("No project selected");

  const main = $("panel-main-view");
  main.innerHTML = `<h3>Editor</h3><p>Loading ${path}...</p>`;

  const res = await apiPost("/api/files/read", {
    project_name: currentProjectName,
    path,
  });

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
    const r = await apiPost("/api/files/write", {
      project_name: currentProjectName,
      path: currentFilePath,
      content: textarea.value,
    });
    if (r.success) {
      showMainMessage("Saved.");
      refreshFileTree(currentProjectName);
    } else alert(r.error || "Save failed");
  });

  $("editor-revert").addEventListener("click", () => openFile(currentFilePath));

  $("editor-download").addEventListener("click", () => {
    const blob = new Blob([textarea.value], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = currentFilePath.split("/").pop();
    a.click();
  });
}

/* ---------------- Preview ---------------- */
function loadPreview(projectName) {
  const panel = $("panel-preview");
  if (!panel) return;

  panel.innerHTML = `<h3>Preview</h3>`;
  const iframe = document.createElement("iframe");
  iframe.className = "preview-frame";
  iframe.src = `${API_BASE}/preview/${encodeURIComponent(projectName)}`;
  iframe.style.width = "100%";
  iframe.style.height = "600px";

  iframe.addEventListener("error", () => {
    $("errors-output").textContent = "Preview failed to load.";
  });

  panel.appendChild(iframe);
}

/* ---------------- Capabilities ---------------- */
function refreshCapabilities() {
  const panel = $("panel-capabilities");
  if (!panel) return;

  panel.innerHTML = `
    <h3>Capabilities</h3>
    <details open>
      <summary>Core Engines</summary>
      <ul>
        <li>App Generator Engine</li>
        <li>AI Assistant Engine</li>
        <li>File Engine</li>
        <li>Project Manager</li>
        <li>Terminal Engine</li>
        <li>Microcontroller Engine</li>
        <li>MCU Breadboard Lab</li>
      </ul>
    </details>
  `;
}

/* ---------------- UI Helpers ---------------- */
function showMainMessage(msg) {
  const main = $("panel-main-view");
  if (!main) return;

  const el = document.createElement("div");
  el.className = "main-message";
  el.textContent = msg;

  main.prepend(el);
  setTimeout(() => el.remove(), 3000);
}
