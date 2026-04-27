// MCU LAB ENGINE — HYBRID MODE (SAME UI, NEW ENGINE)
console.log("MCU Lab Engine (Hybrid) Loaded");

/* -------------------------------------------------------
   DOM ELEMENTS
------------------------------------------------------- */
const zoomContainer = document.getElementById("zoom-container");
const boardLayer = document.getElementById("board-layer");
const wireLayer = document.getElementById("wire-layer");
const componentLayer = document.getElementById("component-layer");

const netlistEl = document.getElementById("netlist");
const simOut = document.getElementById("sim-output");
const palette = document.getElementById("component-palette");

const boardSelect = document.getElementById("board-select");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const toggleWiringBtn = document.getElementById("toggle-wiring");

const importProjectBtn = document.getElementById("import-project");
const exportNetlistBtn = document.getElementById("export-netlist");
const simulateBtn = document.getElementById("simulate");

/* -------------------------------------------------------
   AI PANEL
------------------------------------------------------- */
const aiPromptEl = document.getElementById("ai-prompt");
const aiOutputEl = document.getElementById("ai-output");
const aiImageResultEl = document.getElementById("ai-image-result");
const aiRunBtn = document.getElementById("ai-run");
const aiSessionIdEl = document.getElementById("ai-session-id");
const aiNewSessionBtn = document.getElementById("ai-new-session");
const aiImageStyleEl = document.getElementById("ai-image-style");
const aiImageResEl = document.getElementById("ai-image-res");
const aiTabs = document.querySelectorAll(".ai-tab");

/* -------------------------------------------------------
   IMAGE SOURCES
------------------------------------------------------- */
const IMAGE_BASE = "/static/breadboard";

const BOARD_IMAGES = {
  "esp32-devkit-v1": `${IMAGE_BASE}/boards/esp32-devkit-v1.png`,
  "esp32-s3": `${IMAGE_BASE}/boards/esp32-s3.png`,
  "esp8266": `${IMAGE_BASE}/boards/esp8266.png`,
};

/* -------------------------------------------------------
   LOAD BOARD IMAGE
------------------------------------------------------- */
function loadBoardImage(boardKey) {
  boardLayer.innerHTML = "";
  const img = document.createElement("img");
  img.src = BOARD_IMAGES[boardKey] || BOARD_IMAGES["esp32-devkit-v1"];
  img.draggable = false;
  boardLayer.appendChild(img);
}

loadBoardImage(boardSelect.value);

boardSelect.addEventListener("change", () => {
  loadBoardImage(boardSelect.value);
  rebuildNetlist();
});

/* -------------------------------------------------------
   COMPONENT REGISTRY
------------------------------------------------------- */
const COMPONENT_REGISTRY = {
  led: "LED",
  resistor: "Resistor",
  button: "Button",
  potentiometer: "Potentiometer",
  buzzer: "Buzzer",
  relay: "Relay Module",
  servo: "Servo Motor",
  "stepper-driver": "Stepper Driver A4988",
  dht11: "DHT11",
  dht22: "DHT22",
  bme280: "BME280",
  bmp280: "BMP280",
  mq2: "MQ-2 Gas Sensor",
  mq135: "MQ-135 Air Quality",
  "soil-moisture": "Soil Moisture Sensor",
  "water-level": "Water Level Sensor",
  "rain-sensor": "Rain Sensor",
  pir: "PIR Motion Sensor",
  ultrasonic: "Ultrasonic HC-SR04",
  "tof-vl53l0x": "Laser ToF VL53L0X",
  "ir-obstacle": "IR Obstacle Sensor",
  ldr: "Photoresistor (LDR)",
  "microwave-radar": "Microwave Radar RCWL-0516",
  "laser-emitter": "Laser Emitter",
  "laser-receiver": "Laser Receiver",
  "flame-sensor": "Flame Sensor",
  "sound-sensor": "Sound Sensor",
  "vibration-sensor": "Vibration Sensor",
  "hall-sensor": "Hall Effect Sensor",
  "oled-ssd1306": "OLED SSD1306",
  lcd1602: "LCD 1602",
  lcd2004: "LCD 2004",
  tft18: 'TFT 1.8" SPI',
  nrf24l01: "NRF24L01",
  "lora-sx1278": "LoRa SX1278",
  hc05: "Bluetooth HC-05",
  esp01: "ESP-01 WiFi",
  "rfid-rc522": "RFID RC522",
  buck: "Buck Converter",
  boost: "Boost Converter",
  "battery-holder": "Battery Holder",
  "solar-panel": "Solar Panel",
};

/* -------------------------------------------------------
   PALETTE
------------------------------------------------------- */
palette.innerHTML = "";
Object.entries(COMPONENT_REGISTRY).forEach(([key, label]) => {
  const div = document.createElement("div");
  div.className = "comp";
  div.dataset.type = key;
  div.draggable = true;

  const img = document.createElement("img");
  img.src = `${IMAGE_BASE}/components/${key}.png`;
  img.className = "comp-icon";

  const text = document.createElement("span");
  text.textContent = label;

  div.appendChild(img);
  div.appendChild(text);
  palette.appendChild(div);
});

/* -------------------------------------------------------
   DRAG & DROP COMPONENTS
------------------------------------------------------- */
let draggedType = null;

palette.querySelectorAll(".comp").forEach((c) => {
  c.addEventListener("dragstart", () => {
    draggedType = c.dataset.type;
  });
});

componentLayer.addEventListener("dragover", (e) => e.preventDefault());

componentLayer.addEventListener("drop", (e) => {
  e.preventDefault();
  if (!draggedType) return;

  const rect = componentLayer.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;

  const el = document.createElement("img");
  el.className = "placed-comp";
  el.dataset.type = draggedType;
  el.dataset.id = `C${Date.now()}`;
  el.src = `${IMAGE_BASE}/components/${draggedType}.png`;
  el.style.left = x + "px";
  el.style.top = y + "px";
  el.style.width = "60px";
  el.style.position = "absolute";
  el.style.cursor = "pointer";

  componentLayer.appendChild(el);
  rebuildNetlist();
});

/* -------------------------------------------------------
   WIRES
------------------------------------------------------- */
let wireMode = false;
let wireStart = null;
let wires = [];

const WIRE_COLORS = ["#ef4444", "#000000", "#eab308", "#f97316", "#3b82f6", "#22c55e"];
let wireColorIndex = 0;

function nextWireColor() {
  return WIRE_COLORS[wireColorIndex++ % WIRE_COLORS.length];
}

toggleWiringBtn.addEventListener("click", () => {
  wireMode = !wireMode;
  toggleWiringBtn.classList.toggle("primary", wireMode);
});

componentLayer.addEventListener("click", (e) => {
  if (!wireMode) return;

  const target = e.target;
  if (!target.classList.contains("placed-comp")) return;

  const rect = componentLayer.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;

  const compId = target.dataset.id;

  if (!wireStart) {
    wireStart = { compId, x, y };
  } else {
    const start = wireStart;
    const end = { compId, x, y };
    const color = nextWireColor();

    const wire = {
      id: `W${Date.now()}`,
      from: start.compId,
      to: end.compId,
      x1: start.x,
      y1: start.y,
      x2: end.x,
      y2: end.y,
      color,
    };
    wires.push(wire);
    drawWire(wire);
    wireStart = null;
    rebuildNetlist();
  }
});

function drawWire(wire) {
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("x1", wire.x1);
  line.setAttribute("y1", wire.y1);
  line.setAttribute("x2", wire.x2);
  line.setAttribute("y2", wire.y2);
  line.setAttribute("stroke", wire.color);
  line.setAttribute("stroke-width", "3");
  line.setAttribute("stroke-linecap", "round");
  line.dataset.id = wire.id;
  wireLayer.appendChild(line);
}

/* -------------------------------------------------------
   ZOOM
------------------------------------------------------- */
let zoomLevel = 1;

function applyZoom() {
  zoomContainer.style.transform = `scale(${zoomLevel})`;
}

zoomInBtn.addEventListener("click", () => {
  zoomLevel = Math.min(zoomLevel + 0.1, 2);
  applyZoom();
});

zoomOutBtn.addEventListener("click", () => {
  zoomLevel = Math.max(zoomLevel - 0.1, 0.5);
  applyZoom();
});

/* -------------------------------------------------------
   NETLIST BUILDER
------------------------------------------------------- */
function rebuildNetlist() {
  const comps = [...componentLayer.querySelectorAll(".placed-comp")];
  const components = comps.map((c) => ({
    id: c.dataset.id,
    type: c.dataset.type,
    x: parseInt(c.style.left),
    y: parseInt(c.style.top),
  }));

  const netlist = {
    board: boardSelect.value,
    components,
    wires: wires.map((w) => ({
      id: w.id,
      from: w.from,
      to: w.to,
      x1: w.x1,
      y1: w.y1,
      x2: w.x2,
      y2: w.y2,
      color: w.color,
    })),
  };

  netlistEl.value = JSON.stringify(netlist, null, 2);
}

/* -------------------------------------------------------
   AI REQUEST WRAPPER
------------------------------------------------------- */
async function aiRequest(endpoint, payload) {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

/* -------------------------------------------------------
   AI PANEL
------------------------------------------------------- */
let aiMode = "wiring";

aiTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    aiTabs.forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    aiMode = tab.dataset.mode;
  });
});

aiNewSessionBtn.addEventListener("click", () => {
  aiSessionIdEl.value = `session-${Date.now()}`;
});

aiRunBtn.addEventListener("click", async () => {
  const prompt = aiPromptEl.value.trim();
  if (!prompt) return alert("Enter a prompt");

  const sessionId = aiSessionIdEl.value.trim() || "default-session";
  aiOutputEl.textContent = "Thinking...";
  aiImageResultEl.innerHTML = "";

  let endpoint = "";
  let payload = { prompt, session_id: sessionId };

  if (aiMode === "wiring") endpoint = "/ai/wiring";
  else if (aiMode === "code") endpoint = "/ai/code";
  else if (aiMode === "image") {
    endpoint = "/ai/image";
    payload.style = aiImageStyleEl.value;
    payload.resolution = aiImageResEl.value;
  }

  try {
    const res = await aiRequest(endpoint, payload);

    if (aiMode === "image") {
      aiOutputEl.textContent = res.description || "";
      if (res.image_url) {
        const img = document.createElement("img");
        img.src = res.image_url;
        aiImageResultEl.appendChild(img);
      } else {
        aiImageResultEl.textContent = "No image returned.";
      }
    } else {
      aiOutputEl.textContent = res.text || JSON.stringify(res, null, 2);
    }
  } catch (e) {
    aiOutputEl.textContent = "Error: " + e.message;
  }
});

/* -------------------------------------------------------
   SIMULATION
------------------------------------------------------- */
simulateBtn.addEventListener("click", async () => {
  const net = netlistEl.value.trim();
  if (!net) return alert("Netlist empty");

  simOut.textContent = "Simulating...";

  const res = await aiRequest("/mcu/simulate", { netlist: JSON.parse(net) });
  simOut.textContent = JSON.stringify(res, null, 2);
});

/* -------------------------------------------------------
   IMPORT PROJECT → AUTO WIRING
------------------------------------------------------- */
importProjectBtn.addEventListener("click", async () => {
  const name = prompt("Enter project name:");
  if (!name) return;

  aiOutputEl.textContent = "Loading project...";

  const res = await aiRequest("/mcu/wiring/from-project", { project_name: name });
  aiOutputEl.textContent = JSON.stringify(res, null, 2);

  if (res.netlist) {
    netlistEl.value = JSON.stringify(res.netlist, null, 2);
  }
});

/* -------------------------------------------------------
   EXPORT NETLIST
------------------------------------------------------- */
exportNetlistBtn.addEventListener("click", () => {
  const blob = new Blob([netlistEl.value], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "netlist.json";
  a.click();
});
