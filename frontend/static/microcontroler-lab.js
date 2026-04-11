// MCU LAB ENGINE — UPGRADED
console.log("MCU Lab Loaded");

/* -------------------------------------------------------
   DOM ELEMENTS
------------------------------------------------------- */
const canvas = document.getElementById("breadboard-canvas");
const netlistEl = document.getElementById("netlist");
const aiOut = document.getElementById("ai-output");
const simOut = document.getElementById("sim-output");
const palette = document.getElementById("component-palette");

/* -------------------------------------------------------
   IMAGE SOURCES (LOCAL OR CDN)
------------------------------------------------------- */
const IMAGE_BASE = "/static/breadboard"; 
// If you want CDN instead, replace with:
// const IMAGE_BASE = "https://raw.githubusercontent.com/wokwi/wokwi-assets/main";

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
   AUTO-GENERATE PALETTE
------------------------------------------------------- */
palette.innerHTML = "";
Object.entries(COMPONENT_REGISTRY).forEach(([key, label]) => {
  const div = document.createElement("div");
  div.className = "comp";
  div.dataset.type = key;
  div.draggable = true;

  // Image preview
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

document.querySelectorAll(".comp").forEach((c) => {
  c.addEventListener("dragstart", () => {
    draggedType = c.dataset.type;
  });
});

canvas.addEventListener("dragover", (e) => e.preventDefault());

canvas.addEventListener("drop", (e) => {
  e.preventDefault();
  if (!draggedType) return;

  const el = document.createElement("img");
  el.className = "placed-comp";
  el.dataset.type = draggedType;
  el.src = `${IMAGE_BASE}/components/${draggedType}.png`;
  el.style.position = "absolute";
  el.style.left = e.offsetX + "px";
  el.style.top = e.offsetY + "px";
  el.style.width = "60px";
  el.style.cursor = "pointer";

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
