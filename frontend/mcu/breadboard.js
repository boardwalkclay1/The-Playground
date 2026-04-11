const API_BASE = "/mcu";

const state = {
  components: [],
  nextId: 1,
};

function createComponent(type, x, y) {
  const id = `c${state.nextId++}`;
  const comp = {
    id,
    type,
    x,
    y,
    value_ohm: type === "resistor" ? 330 : undefined,
  };
  state.components.push(comp);
  renderComponents();
  updateNetlistEditor();
}

function renderComponents() {
  const canvas = document.getElementById("breadboardCanvas");
  canvas.innerHTML = "";
  state.components.forEach((c) => {
    const el = document.createElement("div");
    el.className = "breadboard-component";
    el.style.left = c.x + "px";
    el.style.top = c.y + "px";
    el.dataset.id = c.id;

    const label = document.createElement("div");
    label.className = "label";
    label.textContent = `${c.type} (${c.id})`;

    const meta = document.createElement("div");
    meta.className = "meta";
    if (c.type === "resistor") {
      meta.textContent = `${c.value_ohm} Ω`;
    } else {
      meta.textContent = "";
    }

    el.appendChild(label);
    el.appendChild(meta);

    makeDraggable(el, c);
    canvas.appendChild(el);
  });
}

function makeDraggable(el, comp) {
  let dragging = false;
  let startX = 0;
  let startY = 0;
  let origX = 0;
  let origY = 0;

  el.addEventListener("mousedown", (e) => {
    dragging = true;
    startX = e.clientX;
    startY = e.clientY;
    origX = comp.x;
    origY = comp.y;
    document.body.style.userSelect = "none";
  });

  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    comp.x = origX + dx;
    comp.y = origY + dy;
    el.style.left = comp.x + "px";
    el.style.top = comp.y + "px";
  });

  window.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.userSelect = "";
  });
}

function updateNetlistEditor() {
  const vcc = parseFloat(document.getElementById("vccInput").value || "3.3");
  const netlist = {
    board_id: "esp32-devkit-v1",
    vcc,
    components: state.components.map((c) => {
      const base = { id: c.id, type: c.type };
      if (c.type === "resistor") {
        base.value_ohm = c.value_ohm || 330;
      }
      return base;
    }),
    connections: [],
  };
  const editor = document.getElementById("netlistEditor");
  editor.value = JSON.stringify(netlist, null, 2);
}

function readNetlistFromEditor() {
  const editor = document.getElementById("netlistEditor");
  try {
    return JSON.parse(editor.value);
  } catch (e) {
    return null;
  }
}

async function simulate() {
  const projectName = document.getElementById("projectName").value || "esp-lab-1";
  const netlist = readNetlistFromEditor();
  if (!netlist) {
    alert("Netlist JSON is invalid.");
    return;
  }

  const resEl = document.getElementById("simResult");
  const statusEl = resEl.querySelector(".sim-status");
  const issuesEl = resEl.querySelector(".sim-issues");
  const warningsEl = resEl.querySelector(".sim-warnings");

  statusEl.textContent = "Simulating...";
  issuesEl.innerHTML = "";
  warningsEl.innerHTML = "";

  try {
    const resp = await fetch(`${API_BASE}/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_name: projectName, netlist }),
    });
    const data = await resp.json();
    if (!data.success) {
      statusEl.textContent = "Simulation failed.";
      issuesEl.innerHTML = `<div class="issue">${data.error || "Unknown error"}</div>`;
      return;
    }
    const result = data.result;
    statusEl.textContent = result.ok ? "OK: Circuit looks safe." : "Issues detected.";
    issuesEl.innerHTML = "";
    warningsEl.innerHTML = "";

    (result.issues || []).forEach((msg) => {
      const div = document.createElement("div");
      div.className = "issue";
      div.textContent = msg;
      issuesEl.appendChild(div);
    });

    (result.warnings || []).forEach((msg) => {
      const div = document.createElement("div");
      div.className = "warning";
      div.textContent = msg;
      warningsEl.appendChild(div);
    });
  } catch (e) {
    statusEl.textContent = "Simulation error.";
    issuesEl.innerHTML = `<div class="issue">${e.message}</div>`;
  }
}

function initPalette() {
  const palette = document.getElementById("componentPalette");
  const canvas = document.getElementById("breadboardCanvas");

  palette.addEventListener("click", (e) => {
    const item = e.target.closest(".component-item");
    if (!item) return;
    const type = item.dataset.type;
    const rect = canvas.getBoundingClientRect();
    const x = rect.width / 2 - 30;
    const y = rect.height / 2 - 10;
    createComponent(type, x, y);
  });
}

function initSimButton() {
  document.getElementById("simulateBtn").addEventListener("click", simulate);
}

function init() {
  initPalette();
  initSimButton();
  updateNetlistEditor();
}

document.addEventListener("DOMContentLoaded", init);
