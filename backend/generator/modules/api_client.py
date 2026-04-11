# backend/generator/modules/api_client.py
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

from ..base import GenContext, FileOps, GenModule


JS_CLIENT = """// api-client.js
// Lightweight, robust fetch wrapper for browser usage.
// Features: timeout, retries, JSON auto-parsing, auth header support.

function _timeoutPromise(ms, promise) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('Request timed out')), ms);
    promise
      .then((res) => {
        clearTimeout(timer);
        resolve(res);
      })
      .catch((err) => {
        clearTimeout(timer);
        reject(err);
      });
  });
}

export async function apiRequest(path, { method = 'GET', headers = {}, body = null, timeout = 15000, retries = 1 } = {}) {
  const opts = { method, headers: Object.assign({ 'Accept': 'application/json' }, headers) };
  if (body != null) {
    if (typeof body === 'object' && !(body instanceof FormData)) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    } else {
      opts.body = body;
    }
  }

  let lastErr = null;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const fetchPromise = fetch(path, opts);
      const res = await _timeoutPromise(timeout, fetchPromise);
      const contentType = res.headers.get('content-type') || '';
      if (!res.ok) {
        const text = await res.text().catch(() => '');
        const err = new Error(`HTTP ${res.status}: ${res.statusText}`);
        err.status = res.status;
        err.body = text;
        throw err;
      }
      if (contentType.includes('application/json')) {
        return await res.json();
      } else {
        return await res.text();
      }
    } catch (err) {
      lastErr = err;
      // simple exponential backoff
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, 200 * Math.pow(2, attempt)));
        continue;
      }
      throw lastErr;
    }
  }
}
"""

PY_CLIENT = '''# api_client.py
# Lightweight HTTP client helpers using httpx.
# Provides sync and async helpers with retries, timeouts, and optional token auth.

import os
import time
from typing import Any, Dict, Optional
import httpx

DEFAULT_TIMEOUT = 15.0
DEFAULT_RETRIES = 2

def _get_base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")

def _get_auth_header(token: Optional[str]) -> Dict[str, str]:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def request_sync(path: str, method: str = "GET", json_body: Any = None, headers: Optional[Dict[str, str]] = None, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES, token: Optional[str] = None) -> Dict[str, Any]:
    url = _get_base_url().rstrip("/") + "/" + path.lstrip("/")
    headers = headers or {}
    headers.update(_get_auth_header(token))
    last_exc = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(method, url, json=json_body, headers=headers)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    return resp.json()
                return {"text": resp.text}
        except Exception as e:
            last_exc = e
            time.sleep(0.2 * (2 ** attempt))
    raise last_exc

async def request_async(path: str, method: str = "GET", json_body: Any = None, headers: Optional[Dict[str, str]] = None, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES, token: Optional[str] = None) -> Dict[str, Any]:
    url = _get_base_url().rstrip("/") + "/" + path.lstrip("/")
    headers = headers or {}
    headers.update(_get_auth_header(token))
    last_exc = None
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.request(method, url, json=json_body, headers=headers)
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                if "application/json" in content_type:
                    return resp.json()
                return {"text": resp.text}
        except Exception as e:
            last_exc = e
            await asyncio.sleep(0.2 * (2 ** attempt))
    raise last_exc
'''

README_SNIPPET = """# API Client

This project includes two small API client helpers:

- **api-client.js** — browser-friendly `fetch` wrapper with timeout and retries.
- **api_client.py** — Python `httpx` helpers (sync and async) with retries and optional token auth.

Usage:
- JS: `import { apiRequest } from '/api-client.js'; await apiRequest('/api/projects');`
- Python: `from api_client import request_sync; request_sync('/api/projects')`

Set `API_BASE_URL` environment variable to change the default base URL for the Python client.
"""

class APIClientModule(GenModule):
    """
    Adds a generic API client (JS + Python) into the generated project.
    """

    def run(self, ctx: GenContext) -> None:
        root: Path = ctx.project_path
        FileOps.ensure_dir(root, ctx)

        try:
            # Write JS client
            FileOps.write_file(root / "api-client.js", JS_CLIENT, ctx)

            # Write Python client (requires httpx in runtime if used)
            FileOps.write_file(root / "api_client.py", PY_CLIENT, ctx)

            # Write README snippet
            FileOps.write_file(root / "API_CLIENT.md", README_SNIPPET, ctx)

            # Update metadata to indicate API client was added
            try:
                meta_path = root / "metadata.json"
                meta = {}
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta.setdefault("features", [])
                if "api_client" not in meta["features"]:
                    meta["features"].append("api_client")
                meta["last_api_client_added_at"] = datetime.utcnow().isoformat() + "Z"
                FileOps.write_file(meta_path, json.dumps(meta, indent=2), ctx)
            except Exception:
                # non-fatal
                pass

            ctx.log("API client module added", {"path": str(root / "api-client.js")})
        except Exception as e:
            try:
                ctx.error(f"APIClientModule failed: {e}")
            except Exception:
                ctx.log(f"APIClientModule failed: {e}")
            raise
