// MCU LAB ENGINE — microcontroller-lab.js

console.log("MCU Lab Loaded");

const canvas = document.getElementById("breadboard-canvas");
const netlistEl = document.getElementById("netlist");
const aiOut = document.getElementById("ai-output");
const simOut = document.getElementById("sim-output");

/* -------------------------------------------------------
   DRAG & DROP COMPONENTS
------------------------------------------------------- */
let draggedType = null;

document.querySelectorAll(".comp").forEach((c) => {
  c.addEventListener("dragstart", () => {
    draggedType = c.dataset.type;
  });
});

canvas.addEventListener("dragover", (e) => e.preventDefault());

canvas.addEventListener("drop", (e) => {
  e.preventDefault();
  if (!draggedType) return;

  const el = document.createElement("div");
  el.className = "placed-comp";
  el.dataset.type = draggedType;
  el.style.position = "absolute";
  el.style.left = e.offsetX + "px";
  el.style.top = e.offsetY + "px";
  el.style.padding = "6px 10px";
  el.style.background = "#1a2235";
  el.style.border = "1px solid #2b3148";
  el.style.borderRadius = "6px";
  el.style.cursor = "pointer";
  el.textContent = draggedType;

  canvas.appendChild(el);
  rebuildNetlist();
});

/* -------------------------------------------------------
   NETLIST BUILDER
------------------------------------------------------- */
function rebuildNetlist() {
  const comps = [...canvas.querySelectorAll(".placed-comp")];
  const list = comps.map((c, i) => ({
    id: `C${i + 1}`,
    type: c.dataset.type,
    x: parseInt(c.style.left),
    y: parseInt(c.style.top),
  }));

  netlistEl.value = JSON.stringify({ components: list }, null, 2);
}

/* -------------------------------------------------------
   AI WIRING ASSISTANT
------------------------------------------------------- */
async function aiRequest(endpoint, payload) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

document.getElementById("ai-wiring-run").addEventListener("click", async () => {
  const prompt = document.getElementById("ai-wiring-input").value.trim();
  if (!prompt) return alert("Enter wiring description");

  aiOut.textContent = "Thinking...";

  const res = await aiRequest("/mcu/wiring/describe", { prompt });
  aiOut.textContent = JSON.stringify(res, null, 2);

  if (res.netlist) {
    netlistEl.value = JSON.stringify(res.netlist, null, 2);
  }
});

document.getElementById("ai-wiring-from-code").addEventListener("click", async () => {
  const prompt = document.getElementById("ai-wiring-input").value.trim();
  if (!prompt) return alert("Paste code first");

  aiOut.textContent = "Analyzing code...";

  const res = await aiRequest("/mcu/wiring/from-code", { code: prompt });
  aiOut.textContent = JSON.stringify(res, null, 2);

  if (res.netlist) {
    netlistEl.value = JSON.stringify(res.netlist, null, 2);
  }
});

document.getElementById("ai-code-from-wiring").addEventListener("click", async () => {
  const net = netlistEl.value.trim();
  if (!net) return alert("Netlist empty");

  aiOut.textContent = "Generating code...";

  const res = await aiRequest("/mcu/code/from-wiring", { netlist: JSON.parse(net) });
  aiOut.textContent = res.code || JSON.stringify(res, null, 2);
});

/* -------------------------------------------------------
   SIMULATION
------------------------------------------------------- */
document.getElementById("simulate").addEventListener("click", async () => {
  const net = netlistEl.value.trim();
  if (!net) return alert("Netlist empty");

  simOut.textContent = "Simulating...";

  const res = await aiRequest("/mcu/simulate", { netlist: JSON.parse(net) });
  simOut.textContent = JSON.stringify(res, null, 2);
});

/* -------------------------------------------------------
   IMPORT FIRMWARE PROJECT → AUTO WIRING
------------------------------------------------------- */
document.getElementById("import-project").addEventListener("click", async () => {
  const name = prompt("Enter project name:");
  if (!name) return;

  aiOut.textContent = "Loading project...";

  const res = await aiRequest("/mcu/wiring/from-project", { project_name: name });
  aiOut.textContent = JSON.stringify(res, null, 2);

  if (res.netlist) {
    netlistEl.value = JSON.stringify(res.netlist, null, 2);
  }
});

/* -------------------------------------------------------
   EXPORT NETLIST
------------------------------------------------------- */
document.getElementById("export-netlist").addEventListener("click", () => {
  const blob = new Blob([netlistEl.value], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "netlist.json";
  a.click();
});
