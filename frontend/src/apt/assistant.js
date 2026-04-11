// frontend/src/api/assistant.js

export async function runAssistant(prompt, projectName = null) {
  const body = {
    prompt,
    project_name: projectName || null
  };

  const res = await fetch("/api/assistant/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    throw new Error("Assistant request failed");
  }

  return await res.json();
}

// AI PANEL ROUTES
export async function runWiring(prompt, sessionId) {
  const res = await fetch("/api/ai/wiring", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, session_id: sessionId })
  });

  return await res.json();
}

export async function runCode(prompt, sessionId) {
  const res = await fetch("/api/ai/code", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, session_id: sessionId })
  });

  return await res.json();
}

export async function runImage(prompt, style, resolution, sessionId) {
  const res = await fetch("/api/ai/image", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      prompt,
      style,
      resolution,
      session_id: sessionId
    })
  });

  return await res.json();
}
