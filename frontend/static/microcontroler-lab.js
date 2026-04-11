/* -------------------------------------------------------
   AI PANEL PRO
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

let aiMode = "wiring"; // wiring | code | image

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

  if (aiMode === "wiring") {
    endpoint = "/ai/wiring";
  } else if (aiMode === "code") {
    endpoint = "/ai/code";
  } else if (aiMode === "image") {
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
