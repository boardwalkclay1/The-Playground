// MCU LAB ENGINE — PRO
console.log("MCU Lab Loaded");

/* -------------------------------------------------------
   DOM ELEMENTS
------------------------------------------------------- */
const zoomContainer = document.getElementById("zoom-container");
const boardLayer = document.getElementById("board-layer");
const wireLayer = document.getElementById("wire-layer");
const componentLayer = document.getElementById("component-layer");

const netlistEl = document.getElementById("netlist");
const aiOut = document.getElementById("ai-output");
const simOut = document.getElementById("sim-output");
const palette = document.getElementById("component-palette");

const boardSelect = document.getElementById("board-select");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");
const toggleWiringBtn = document.getElementById("toggle-wiring");

/* -------------------------------------------------------
   IMAGE SOURCES (LOCAL OR CDN)
------------------------------------------------------- */
const IMAGE_BASE = "/static/breadboard";
// If you want CDN instead, replace with:
// const IMAGE_BASE = "https://raw.githubusercontent.com/wokwi/wokwi-assets/main";

/* -------------------------------------------------------
   BOARDS
------------------------------------------------------- */
const BOARD_IMAGES = {
  "esp32-devkit-v1": `${IMAGE_BASE}/boards/esp32-devkit-v1.png`,
  "esp32-s3": `${IMAGE_BASE}/boards/esp32-s3.png`,
  "esp8266": `${IMAGE_BASE}/boards/esp8266.png`,
};

function loadBoardImage(boardKey) {
  boardLayer.innerHTML = "";
  const img = document.createElement("img");
  img.src = BOARD_IMAGES[boardKey] || BOARD_IMAGES["esp32-devkit-v1"];
  boardLayer.appendChild(img);
}

loadBoardImage(boardSelect.value);

boardSelect.addEventListener("change", () => {
  loadBoardImage(boardSelect.value);
});

/* -------------------------------------------------------
   AUTO-REGISTERED COMPONENTS
------------------------------------------------------- */
const COMPONENT_REGISTRY = {
  // Basic
  led: "LED",
  resistor: "Resistor",
  button: "Button",
  potentiometer: "Potentiometer",
  buzzer: "Buzzer",
  relay: "Relay Module",
  servo: "Servo Motor",
  "stepper-driver": "Stepper Driver A4988",

  // Environmental
  dht11: "DHT11",
  dht22: "DHT22",
  bme280: "BME280",
  bmp280: "BMP280",
  mq2: "MQ-2 Gas Sensor",
  mq135: "MQ-135 Air Quality",
  "soil-moisture": "Soil Moisture Sensor",
  "water-level": "Water Level Sensor",
  "rain-sensor": "Rain Sensor",

  // Motion / Distance / Light
  pir: "PIR Motion Sensor",
  ultrasonic: "Ultrasonic HC-SR04",
  "tof-vl53l0x": "Laser ToF VL53L0X",
  "ir-obstacle": "IR Obstacle Sensor",
  ldr: "Photoresistor (LDR)",

  // Specialty
  "microwave-radar": "Microwave Radar RCWL-0516",
  "laser-emitter": "Laser Emitter",
  "laser-receiver": "Laser Receiver",
  "flame-sensor": "Flame Sensor",
  "sound-sensor": "Sound Sensor",
  "vibration-sensor": "Vibration Sensor",
  "hall-sensor": "Hall Effect Sensor",

  // Displays
  "oled-ssd1306": "OLED SSD1306",
  lcd1602: "LCD 1602",
  lcd2004: "LCD 2004",
  tft18: "TFT 1.8\" SPI",

  // Communication
  nrf24l01: "NRF24L01",
  "lora-sx1278": "LoRa SX1278",
  hc05: "Bluetooth HC-05",
  esp01: "ESP-01 WiFi",
  "rfid-rc522": "RFID RC522",

  // Power
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

const WIRE_COLORS = [
  "#ef4444", // red
  "#000000", // black
  "#eab308", // yellow
  "#f97316", // orange
  "#3b82f6", // blue
  "#22c55e", // green
];
let wireColorIndex = 0;

function nextWireColor() {
  const color = WIRE_COLORS[wireColorIndex % WIRE_COLORS.length];
  wireColorIndex++;
  return color;
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
   AI WIRING ASSISTANT
------------------------------------------------------- */
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
