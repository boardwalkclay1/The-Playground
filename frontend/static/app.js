let currentProjectName = null;

document.addEventListener("DOMContentLoaded", () => {
  setupGeneratorPanel();
  setupAssistantPanel();
});


// -----------------------------------------------------
// GENERATOR PANEL
// -----------------------------------------------------
function setupGeneratorPanel() {
  const promptEl = document.getElementById("generator-input");
  const runBtn = document.getElementById("generator-run");
  const logsEl = document.getElementById("logs-output");
  const errorsEl = document.getElementById("errors-output");

  if (!promptEl || !runBtn) return;

  runBtn.addEventListener("click", async () => {
    const prompt = promptEl.value.trim();
    if (!prompt) {
      if (errorsEl) errorsEl.textContent = "Prompt is empty.";
      return;
    }

    const projectName = "project-" + Date.now();
    currentProjectName = projectName;

    if (logsEl) logsEl.textContent = "Starting generation...\n";
    if (errorsEl) errorsEl.textContent = "";

    try {
      const res = await fetch("/api/generator/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          project_name: projectName,
          app_type: "generic",
        }),
      });

      const data = await res.json();

      if (logsEl && Array.isArray(data.logs)) {
        logsEl.textContent = data.logs
          .map((l) => `[${l.level.toUpperCase()}] ${l.message}`)
          .join("\n");
      }

      if (errorsEl && Array.isArray(data.errors) && data.errors.length > 0) {
        errorsEl.textContent = data.errors.join("\n");
      }

      if (data.success) {
        loadPreview(projectName);
      }
    } catch (e) {
      if (errorsEl) errorsEl.textContent = "Generator error: " + e.message;
    }
  });
}


// -----------------------------------------------------
// AI ASSISTANT PANEL
// -----------------------------------------------------
function setupAssistantPanel() {
  const mainView = document.getElementById("panel-main-view");
  if (!mainView) return;

  const container = document.createElement("div");
  container.className = "assistant-panel";

  const title = document.createElement("h3");
  title.textContent = "AI Assistant";

  const textarea = document.createElement("textarea");
  textarea.id = "assistant-input";
  textarea.placeholder =
    "Tell the assistant what to do inside the current project...";

  const button = document.createElement("button");
  button.id = "assistant-run";
  button.className = "btn btn-primary";
  button.textContent = "Run Assistant";

  const output = document.createElement("pre");
  output.id = "assistant-output";

  container.appendChild(title);
  container.appendChild(textarea);
  container.appendChild(button);
  container.appendChild(output);
  mainView.appendChild(container);

  button.addEventListener("click", async () => {
    const prompt = textarea.value.trim();
    if (!prompt) {
      output.textContent = "Assistant prompt is empty.";
      return;
    }
    if (!currentProjectName) {
      output.textContent = "No project generated yet.";
      return;
    }

    output.textContent = "Assistant running...\n";

    try {
      const res = await fetch("/api/assistant/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          project_name: currentProjectName,
        }),
      });

      const data = await res.json();
      output.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      output.textContent = "Assistant error: " + e.message;
    }
  });
}


// -----------------------------------------------------
// PREVIEW PANEL
// -----------------------------------------------------
function loadPreview(projectName) {
  const previewPanel = document.getElementById("panel-preview");
  if (!previewPanel) return;

  previewPanel.innerHTML = "";

  const iframe = document.createElement("iframe");
  iframe.className = "preview-frame";
  iframe.src = `/preview/${encodeURIComponent(projectName)}`;

  iframe.addEventListener("error", () => {
    const errorsEl = document.getElementById("errors-output");
    if (errorsEl) errorsEl.textContent = "Preview failed to load.";
  });

  previewPanel.appendChild(iframe);
}
