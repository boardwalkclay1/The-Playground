# backend/generator/modules/storage_kv.py
"""
Upgraded KVStorageModule

Improvements:
- Writes a structured kv-config.json describing namespaces and usage notes
- Adds a lightweight kv_client.py helper that provides a local file-backed KV for development
  and a clear adapter point for Cloudflare Workers KV or other hosted KV providers
- Adds a README explaining how to use and adapt the KV client
- Updates project metadata to record that KV support was added
- Uses FileOps and GenContext for safe writes and logging
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

from ..base import GenContext, FileOps, GenModule


DEFAULT_KV_CONFIG = {
    "namespaces": [
        {"name": "app-kv", "purpose": "generic key-value storage", "binding": "APP_KV"}
    ],
    "notes": "This descriptor lists KV namespaces used by the app. Adapt bindings per deployment.",
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "generator": "Boardwalk Playground Studio",
}

KV_CLIENT_PY = '''"""
kv_client.py

Lightweight KV client adapter for generated projects.

- For local development this provides a simple file-backed KV store (JSON file per namespace).
- For production on Cloudflare Workers, replace the LocalKVAdapter with a CloudflareKVAdapter
  that uses the Workers runtime binding (e.g., env["APP_KV"].put/get/delete).
- The adapter interface is intentionally small: get(key), put(key, value), delete(key), list(prefix).

Usage (local):
    from kv_client import LocalKVAdapter
    kv = LocalKVAdapter("app-kv", root="./.kvdata")
    kv.put("foo", {"bar": 1})
    print(kv.get("foo"))

Notes:
- Values are stored as JSON strings. For binary data, extend the adapter accordingly.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

class LocalKVAdapter:
    """
    Simple file-backed KV adapter for local development.
    Stores each namespace as a JSON file under the provided root directory.
    """

    def __init__(self, namespace: str, root: str = "./.kvdata"):
        self.namespace = namespace
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.file = self.root / f"{self.namespace}.json"
        if not self.file.exists():
            self._write({})

    def _read(self) -> Dict[str, Any]:
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _write(self, data: Dict[str, Any]) -> None:
        self.file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get(self, key: str) -> Optional[Any]:
        data = self._read()
        return data.get(key)

    def put(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def delete(self, key: str) -> bool:
        data = self._read()
        if key in data:
            del data[key]
            self._write(data)
            return True
        return False

    def list(self, prefix: str = "") -> List[str]:
        data = self._read()
        if not prefix:
            return list(data.keys())
        return [k for k in data.keys() if k.startswith(prefix)]


class CloudflareKVAdapter:
    """
    Adapter placeholder for Cloudflare Workers KV.

    In a Workers environment you would implement this adapter to call the binding:
      env["APP_KV"].get(key)
      env["APP_KV"].put(key, value)
      env["APP_KV"].delete(key)

    This class is a stub to show the expected interface.
    """

    def __init__(self, binding_name: str):
        self.binding_name = binding_name
        raise NotImplementedError("CloudflareKVAdapter must be implemented in the Workers runtime environment")

    def get(self, key: str):
        raise NotImplementedError

    def put(self, key: str, value):
        raise NotImplementedError

    def delete(self, key: str):
        raise NotImplementedError

    def list(self, prefix: str = ""):
        raise NotImplementedError
'''

KV_README = """# KV Storage (Key-Value)

This project includes a KV descriptor and a small local KV adapter for development.

Files added:
- `kv-config.json` — descriptor listing namespaces and intended bindings.
- `kv_client.py` — LocalKVAdapter for local development and a CloudflareKVAdapter stub for production.
- `KV_README.md` — this file.

Local development:
- The LocalKVAdapter stores namespace data under `./.kvdata/<namespace>.json`.
- Example:
    from kv_client import LocalKVAdapter
    kv = LocalKVAdapter("app-kv")
    kv.put("greeting", {"text": "hello"})
    print(kv.get("greeting"))

Cloudflare Workers:
- Replace LocalKVAdapter usage with a Cloudflare binding, e.g. env["APP_KV"].get/put/delete.
- The CloudflareKVAdapter in kv_client.py is a stub showing the expected interface.

Security:
- Do not store secrets in plain text in KV without encryption.
- Consider rotating keys and using environment variables for sensitive configuration.
"""

class KVStorageModule(GenModule):
    """
    Generates KV config and helper files for key-value storage.
    """

    def run(self, ctx: GenContext) -> None:
        root: Path = ctx.project_path
        FileOps.ensure_dir(root, ctx)

        try:
            # Write kv-config.json
            cfg = DEFAULT_KV_CONFIG.copy()
            # allow GenContext to override or provide namespaces
            try:
                user_cfg = getattr(ctx, "kv_config", None)
                if isinstance(user_cfg, dict):
                    # merge namespaces if provided
                    if "namespaces" in user_cfg:
                        cfg["namespaces"] = user_cfg["namespaces"]
                    cfg.update({k: v for k, v in user_cfg.items() if k != "namespaces"})
            except Exception:
                pass
            FileOps.write_file(root / "kv-config.json", json.dumps(cfg, indent=2), ctx)

            # Write kv_client.py
            FileOps.write_file(root / "kv_client.py", KV_CLIENT_PY, ctx)

            # Write README
            FileOps.write_file(root / "KV_README.md", KV_README, ctx)

            # Update metadata
            try:
                meta_path = root / "metadata.json"
                meta = {}
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta.setdefault("features", [])
                if "kv_storage" not in meta["features"]:
                    meta["features"].append("kv_storage")
                meta["kv_storage_added_at"] = datetime.utcnow().isoformat() + "Z"
                FileOps.write_file(meta_path, json.dumps(meta, indent=2), ctx)
            except Exception:
                pass

            ctx.log("KV storage config and helpers created", {"path": str(root / "kv-config.json")})
        except Exception as e:
            try:
                ctx.error(f"KVStorageModule failed: {e}")
            except Exception:
                ctx.log(f"KVStorageModule failed: {e}")
            raise
