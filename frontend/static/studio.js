// static/studio.js
// Single-file frontend for Project Manager, File Tree, Editor, Terminal, Microcontroller

let currentProject = null;
let currentFile = null;

document.addEventListener("DOMContentLoaded", () => {
  wireProjectManager();
  wireFileTree();
  wireEditorActions();
  wireTerminal();
  wireMicrocontroller();
  refreshProjects();
});

// simple fetch helper
async function postJSON(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function getJSON(path) {
  const res = await fetch(path);
  return res.json();
}

/* ---------------- Projects ---------------- */
function wireProjectManager() {
  const panel = document.getElementById("panel-projects");
  if (!panel) return;
  panel.innerHTML = `
    <h3>Projects</h3>
    <div class="pm-controls">
      <input id="pm-new-name" placeholder="new project name" />
      <button id="pm-create" class="btn">Create</button>
    </div>
    <div id="pm-list"></div>
  `;
  document.getElementById("pm-create").addEventListener("click", async () => {
    const name = document.getElementById("pm-new-name").value.trim();
    if (!name) return alert("Enter a project name");
    const res = await postJSON("/api/projects/create", { name });
    if (res.success) {
      refreshProjects();
      document.getElementById("pm-new-name").value = "";
    } else {
      alert(res.error || "Create failed");
    }
  });
}

async function refreshProjects() {
  const data = await getJSON("/api/projects");
  const list = document.getElementById("pm-list");
  if (!list) return;
  list.innerHTML = "";
  if (!data.success) {
    list.textContent = "Failed to load projects";
    return;
  }
  data.projects.forEach((p) => {
    const el = document.createElement("div");
    el.className = "pm-item";
    el.innerHTML = `
      <span class="pm-name">${p}</span>
      <button class="btn pm-open">Open</button>
      <button class="btn pm-dup">Duplicate</button>
      <button class="btn pm-del">Delete</button>
    `;
    el.querySelector(".pm-open").addEventListener("click", () => {
      currentProject = p;
      refreshFileTree();
      loadPreview(p);
    });
    el.querySelector(".pm-dup").addEventListener("click", async () => {
      const res = await postJSON("/api/projects/duplicate", { name: p });
      if (res.success) refreshProjects();
      else alert(res.error || "Duplicate failed");
    });
    el.querySelector(".pm-del").addEventListener("click", async () => {
      if (!confirm(`Delete project ${p}?`)) return;
      const res = await postJSON("/api/projects/delete", { name: p });
      if (res.success) {
        if (currentProject === p) {
          currentProject = null;
          document.getElementById("panel-filetree").innerHTML = "";
          document.getElementById("panel-main-view").innerHTML = "";
        }
        refreshProjects();
      } else alert(res.error || "Delete failed");
    });
    list.appendChild(el);
  });
}

/* ---------------- File Tree ---------------- */
function wireFileTree() {
  const panel = document.getElementById("panel-filetree");
  if (!panel) return;
  panel.innerHTML = `<h3>File Tree</h3><div id="ft-root">No project selected</div>`;
}

async function refreshFileTree() {
  const root = document.getElementById("ft-root");
  if (!root) return;
  if (!currentProject) {
    root.innerHTML = "No project selected";
    return;
  }
  root.innerHTML = "Loading...";
  const res = await getJSON(`/api/files/tree/${encodeURIComponent(currentProject)}`);
  if (!res.success) {
    root.innerHTML = "Failed to load file tree";
    return;
  }
  root.innerHTML = "";
  const ul = document.createElement("ul");
  ul.className = "ft-ul";
  function render(nodes, parent) {
    nodes.forEach((n) => {
      const li = document.createElement("li");
      li.className = `ft-node ft-${n.type}`;
      const label = document.createElement("span");
      label.textContent = n.name;
      label.dataset.path = n.path;
      label.addEventListener("click", () => {
        if (n.type === "file") openFile(n.path);
      });
      li.appendChild(label);
      if (n.type === "dir" && Array.isArray(n.children)) {
        const childUl = document.createElement("ul");
        render(n.children, childUl);
        li.appendChild(childUl);
      }
      parent.appendChild(li);
    });
  }
  render(res.tree, ul);
  root.appendChild(ul);

  // file operations UI
  const ops = document.createElement("div");
  ops.className = "ft-ops";
  ops.innerHTML = `
    <input id="ft-new-path" placeholder="path/to/newfile.txt" />
    <button id="ft-create" class="btn">Create File</button>
    <input id="ft-delete-path" placeholder="path/to/delete" />
    <button id="ft-delete" class="btn">Delete</button>
    <input id="ft-move-src" placeholder="src/path" />
    <input id="ft-move-dst" placeholder="dst/path" />
    <button id="ft-move" class="btn">Move</button>
  `;
  root.appendChild(ops);

  document.getElementById("ft-create").addEventListener("click", async () => {
    const path = document.getElementById("ft-new-path").value.trim();
    if (!path) return alert("Enter path");
    const res = await postJSON("/api/files/write", { project_name: currentProject, path, content: "" });
    if (res.success) refreshFileTree();
    else alert(res.error || "Create failed");
  });

  document.getElementById("ft-delete").addEventListener("click", async () => {
    const path = document.getElementById("ft-delete-path").value.trim();
    if (!path) return alert("Enter path");
    const res = await postJSON("/api/files/delete", { project_name: currentProject, path });
    if (res.success) refreshFileTree();
    else alert(res.error || "Delete failed");
  });

  document.getElementById("ft-move").addEventListener("click", async () => {
    const src = document.getElementById("ft-move-src").value.trim();
    const dst = document.getElementById("ft-move-dst").value.trim();
    if (!src || !dst) return alert("Enter src and dst");
    const res = await postJSON("/api/files/move", { project_name: currentProject, src, dst });
    if (res.success) refreshFileTree();
    else alert(res.error || "Move failed");
  });
}

/* ---------------- Editor ---------------- */
function wireEditorActions() {
  // editor actions are triggered by openFile
}

async function openFile(path) {
  if (!currentProject) return alert("No project selected");
  const main = document.getElementById("panel-main-view");
  main.innerHTML = "<h3>Editor</h3><p>Loading...</p>";
  const res = await postJSON("/api/files/read", { project_name: currentProject, path });
  if (!res.success) {
    main.innerHTML = "<h3>Editor</h3><p>Failed to load file</p>";
    return;
  }
  currentFile = path;
  const wrapper = document.createElement("div");
  wrapper.className = "editor";

  const title = document.createElement("div");
  title.className = "editor-title";
  title.textContent = `${currentProject} / ${path}`;

  const ta = document.createElement("textarea");
  ta.className = "editor-textarea";
  ta.value = res.content;

  const save = document.createElement("button");
  save.className = "btn";
  save.textContent = "Save";
  save.addEventListener("click", async () => {
    const r = await postJSON("/api/files/write", { project_name: currentProject, path: currentFile, content: ta.value });
    if (r.success) {
      alert("Saved");
      refreshFileTree();
    } else alert(r.error || "Save failed");
  });

  wrapper.appendChild(title);
  wrapper.appendChild(ta);
  wrapper.appendChild(save);
  main.innerHTML = "";
  main.appendChild(wrapper);
}

/* ---------------- Terminal ---------------- */
function wireTerminal() {
  const panel = document.getElementById("panel-terminal");
  if (!panel) return;
  panel.innerHTML = `
    <h3>Terminal</h3>
    <div>
      <input id="term-cmd" placeholder="git status" />
      <button id="term-run" class="btn">Run</button>
    </div>
    <pre id="term-out"></pre>
  `;
  document.getElementById("term-run").addEventListener("click", async () => {
    const cmd = document.getElementById("term-cmd").value.trim();
    if (!cmd) return alert("Enter command");
    if (!currentProject) return alert("Select a project first");
    const out = document.getElementById("term-out");
    out.textContent = "Running...";
    const res = await postJSON("/api/terminal/run", { project_name: currentProject, command: cmd });
    out.textContent = JSON.stringify(res, null, 2);
  });
}

/* ---------------- Microcontroller ---------------- */
function wireMicrocontroller() {
  const panel = document.getElementById("panel-microcontroller");
  if (!panel) return;
  panel.innerHTML = `
    <h3>Microcontroller Builder</h3>
    <textarea id="mcu-prompt" placeholder="Describe firmware or sketch"></textarea>
    <div>
      <input id="mcu-project" placeholder="project name (optional)" />
      <button id="mcu-gen" class="btn">Generate Firmware</button>
      <button id="mcu-flash" class="btn">Flash (stub)</button>
    </div>
    <pre id="mcu-out"></pre>
  `;
  document.getElementById("mcu-gen").addEventListener("click", async () => {
    const prompt = document.getElementById("mcu-prompt").value.trim();
    const project = document.getElementById("mcu-project").value.trim() || "mcu-sandbox";
    if (!prompt) return alert("Enter prompt");
    const out = document.getElementById("mcu-out");
    out.textContent = "Generating...";
    const res = await postJSON("/api/microcontroller/generate", { project_name: project, prompt });
    out.textContent = JSON.stringify(res, null, 2);
    // refresh file tree if sandbox used
    if (currentProject === project) refreshFileTree();
  });
  document.getElementById("mcu-flash").addEventListener("click", async () => {
    const project = document.getElementById("mcu-project").value.trim() || "mcu-sandbox";
    const out = document.getElementById("mcu-out");
    out.textContent = "Flashing (stub)...";
    const res = await postJSON("/api/microcontroller/flash", { project_name: project, port: null });
    out.textContent = JSON.stringify(res, null, 2);
  });
}

/* ---------------- Preview helper ---------------- */
function loadPreview(project) {
  const panel = document.getElementById("panel-preview");
  if (!panel) return;
  panel.innerHTML = "";
  const iframe = document.createElement("iframe");
  iframe.src = `/preview/${encodeURIComponent(project)}`;
  iframe.className = "preview-frame";
  panel.appendChild(iframe);
}
