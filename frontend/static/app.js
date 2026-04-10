// =====================================================
// GLOBAL STATE
// =====================================================
let currentProjectName = null;
let currentFilePath = null;


// =====================================================
// ON LOAD
// =====================================================
document.addEventListener("DOMContentLoaded", () => {
  setupGeneratorPanel();
  setupAssistantPanel();
  setupTerminalPanel();
  setupMicrocontrollerPanel();

  setupProjectsPanel();
  setupFileTreePanel();
  setupCapabilitiesPanel();
});


// =====================================================
// UNIVERSAL API HELPER
// =====================================================
async function api(path, method = "GET", body = null) {
  try {
    const res = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : null,
    });
    return await res.json();
  } catch (err) {
    console.error("API ERROR:", err);
    return { success: false, error: err.message };
  }
}


// =====================================================
// GENERATOR PANEL
// =====================================================
function setupGeneratorPanel() {
  const promptEl = document.getElementById("generator-input");
  const runBtn = document.getElementById("generator-run");
  const logsEl = document.getElementById("logs-output");
  const errorsEl = document.getElementById("errors-output");

  if (!promptEl || !runBtn) return;

  runBtn.addEventListener("click", async () => {
    const prompt = promptEl.value.trim();
    if (!prompt) {
      errorsEl.textContent = "Prompt is empty.";
      return;
    }

    const projectName = "project-" + Date.now();
    currentProjectName = projectName;

    logsEl.textContent = "Starting generation...\n";
    errorsEl.textContent = "";

    const data = await api("/api/generator/run", "POST", {
      prompt,
      project_name: projectName,
      app_type: "generic",
    });

    if (Array.isArray(data.logs)) {
      logsEl.textContent = data.logs
        .map((l) => `[${l.level.toUpperCase()}] ${l.message}`)
        .join("\n");
    }

    if (Array.isArray(data.errors) && data.errors.length > 0) {
      errorsEl.textContent = data.errors.join("\n");
    }

    if (data.success) {
      loadPreview(projectName);
      loadFileTree(projectName);
      loadProjectsList();
    }
  });
}


// =====================================================
// AI ASSISTANT PANEL
// =====================================================
function setupAssistantPanel() {
  const input = document.getElementById("assistant-input");
  const runBtn = document.getElementById("assistant-run");
  const output = document.getElementById("assistant-output");

  if (!input || !runBtn) return;

  runBtn.addEventListener("click", async () => {
    const prompt = input.value.trim();
    if (!prompt) {
      output.textContent = "Assistant prompt is empty.";
      return;
    }
    if (!currentProjectName) {
      output.textContent = "No project generated yet.";
      return;
    }

    output.textContent = "Assistant running...\n";

    const data = await api("/api/assistant/run", "POST", {
      prompt,
      project_name: currentProjectName,
    });

    output.textContent = JSON.stringify(data, null, 2);

    // Refresh file tree if assistant changed files
    loadFileTree(currentProjectName);
  });
}


// =====================================================
// TERMINAL PANEL
// =====================================================
function setupTerminalPanel() {
  const input = document.getElementById("terminal-input");
  const runBtn = document.getElementById("terminal-run");
  const output = document.getElementById("terminal-output");

  if (!input || !runBtn) return;

  runBtn.addEventListener("click", async () => {
    const command = input.value.trim();
    if (!command) {
      output.textContent = "Command is empty.";
      return;
    }
    if (!currentProjectName) {
      output.textContent = "No project selected.";
      return;
    }

    output.textContent = "Running command...\n";

    const data = await api("/api/assistant/run", "POST", {
      prompt: `run command: ${command}`,
      project_name: currentProjectName,
    });

    output.textContent = JSON.stringify(data, null, 2);
  });
}


// =====================================================
// MICROCONTROLLER PANEL
// =====================================================
function setupMicrocontrollerPanel() {
  const input = document.getElementById("mcu-input");
  const runBtn = document.getElementById("mcu-run");
  const output = document.getElementById("mcu-output");

  if (!input || !runBtn) return;

  runBtn.addEventListener("click", async () => {
    const prompt = input.value.trim();
    if (!prompt) {
      output.textContent = "Microcontroller prompt is empty.";
      return;
    }

    output.textContent = "Generating firmware...\n";

    const data = await api("/api/assistant/run", "POST", {
      prompt: `microcontroller: ${prompt}`,
      project_name: currentProjectName,
    });

    output.textContent = JSON.stringify(data, null, 2);
  });
}


// =====================================================
// PREVIEW PANEL
// =====================================================
function loadPreview(projectName) {
  const previewPanel = document.getElementById("panel-preview");
  previewPanel.innerHTML = "";

  const iframe = document.createElement("iframe");
  iframe.className = "preview-frame";
  iframe.src = `/preview/${encodeURIComponent(projectName)}`;

  iframe.addEventListener("error", () => {
    const errorsEl = document.getElementById("errors-output");
    errorsEl.textContent = "Preview failed to load.";
  });

  previewPanel.appendChild(iframe);
}


// =====================================================
// PROJECTS PANEL (placeholder)
// =====================================================
function setupProjectsPanel() {
  loadProjectsList();
}

function loadProjectsList() {
  const panel = document.getElementById("panel-projects");
  panel.innerHTML = "<h3>Projects</h3><p>Coming soon...</p>";
}


// =====================================================
// FILE TREE PANEL (placeholder)
// =====================================================
function setupFileTreePanel() {
  loadFileTree();
}

function loadFileTree() {
  const panel = document.getElementById("panel-filetree");
  panel.innerHTML = "<h3>File Tree</h3><p>Coming soon...</p>";
}


// =====================================================
// CAPABILITIES PANEL (placeholder)
// =====================================================
function setupCapabilitiesPanel() {
  const panel = document.getElementById("panel-capabilities");
  panel.innerHTML = `
    <h3>Capabilities</h3>
    <ul>
      <li>App Generator Engine</li>
      <li>AI Assistant Engine</li>
      <li>Terminal Engine</li>
      <li>Microcontroller Engine</li>
      <li>File Engine</li>
      <li>Cloudflare Engine</li>
      <li>Project Manager Engine</li>
    </ul>
  `;
}
