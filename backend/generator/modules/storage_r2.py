# backend/generator/modules/storage_r2.py
"""
Upgraded R2StorageModule

Improvements:
- Writes a structured r2-config.json describing buckets and usage notes
- Adds a lightweight r2_client.py adapter that provides a local file-backed storage
  for development and a clear adapter point for Cloudflare R2 or S3-compatible providers
- Adds a README explaining how to use and adapt the R2 client
- Updates project metadata to record that R2 support was added
- Uses FileOps and GenContext for safe writes and logging
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

from ..base import GenContext, FileOps, GenModule

DEFAULT_R2_CONFIG = {
    "buckets": [
        {"name": "media", "purpose": "app media storage", "binding": "MEDIA_R2"}
    ],
    "notes": "This descriptor lists object storage buckets used by the app. Adapt bindings per deployment.",
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "generator": "Boardwalk Playground Studio",
}

R2_CLIENT_PY = '''"""
r2_client.py

Lightweight R2/S3 adapter for generated projects.

- Local development: LocalR2Adapter stores objects under ./r2_data/<bucket> as files.
- Production: implement CloudflareR2Adapter or S3Adapter to call the real provider.
- Interface: put(key, bytes_or_text), get(key) -> bytes, delete(key), list(prefix)

Usage (local):
    from r2_client import LocalR2Adapter
    r2 = LocalR2Adapter("media", root="./.r2data")
    r2.put("images/logo.png", b"...")
    data = r2.get("images/logo.png")
"""

import os
from pathlib import Path
from typing import Optional, List, Any

ROOT = Path(__file__).parent

class LocalR2Adapter:
    """
    Simple file-backed object store for local development.
    Stores objects under root/<bucket>/<key> as files.
    """

    def __init__(self, bucket: str, root: str = "./.r2data"):
        self.bucket = bucket
        self.root = Path(root)
        self.bucket_dir = self.root / bucket
        self.bucket_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, key: str) -> Path:
        # normalize key to avoid path traversal
        safe_key = key.lstrip("/").replace("..", "")
        return self.bucket_dir / safe_key

    def put(self, key: str, data: bytes) -> dict:
        p = self._path_for(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("wb") as f:
            f.write(data)
        return {"success": True, "path": str(p)}

    def get(self, key: str) -> Optional[bytes]:
        p = self._path_for(key)
        if not p.exists() or not p.is_file():
            return None
        return p.read_bytes()

    def delete(self, key: str) -> bool:
        p = self._path_for(key)
        if p.exists():
            p.unlink()
            return True
        return False

    def list(self, prefix: str = "") -> List[str]:
        out = []
        base = self.bucket_dir
        if not base.exists():
            return out
        for p in base.rglob("*"):
            if p.is_file():
                rel = p.relative_to(base).as_posix()
                if prefix:
                    if rel.startswith(prefix):
                        out.append(rel)
                else:
                    out.append(rel)
        return out

class S3Adapter:
    """
    Minimal S3-compatible adapter placeholder.

    To use in production, implement using boto3 or another S3 client:
      - put: s3_client.put_object(Bucket=bucket, Key=key, Body=data)
      - get: s3_client.get_object(...)
      - delete: s3_client.delete_object(...)
      - list: s3_client.list_objects_v2(...)
    """
    def __init__(self, bucket: str, client=None):
        self.bucket = bucket
        self.client = client
        raise NotImplementedError("S3Adapter must be implemented with a real S3 client")

    def put(self, key: str, data: bytes):
        raise NotImplementedError

    def get(self, key: str):
        raise NotImplementedError

    def delete(self, key: str):
        raise NotImplementedError

    def list(self, prefix: str = ""):
        raise NotImplementedError
'''

R2_README = """# R2 / Object Storage

This project includes:
- `r2-config.json` — descriptor listing buckets and intended bindings.
- `r2_client.py` — LocalR2Adapter for local development and adapter stubs for production (S3/Cloudflare R2).
- `R2_README.md` — this file.

Local development:
- LocalR2Adapter stores objects under `./.r2data/<bucket>/<key>`.
- Example:
    from r2_client import LocalR2Adapter
    r2 = LocalR2Adapter("media")
    r2.put("images/logo.png", open("logo.png","rb").read())
    print(r2.list("images/"))

Cloudflare R2 / S3:
- Replace LocalR2Adapter usage with a production adapter that uses the provider SDK.
- Keep credentials and secrets in environment variables; do not commit them.

Security:
- Do not store sensitive secrets in object storage without encryption.
- Use signed URLs or short-lived credentials for client uploads when exposing storage to browsers.
"""

class R2StorageModule(GenModule):
    """
    Generates R2 config and helper files for object storage.
    """

    def run(self, ctx: GenContext) -> None:
        root: Path = ctx.project_path
        FileOps.ensure_dir(root, ctx)

        try:
            # Write r2-config.json
            cfg = DEFAULT_R2_CONFIG.copy()
            # allow GenContext to override or provide buckets
            try:
                user_cfg = getattr(ctx, "r2_config", None)
                if isinstance(user_cfg, dict):
                    if "buckets" in user_cfg:
                        cfg["buckets"] = user_cfg["buckets"]
                    cfg.update({k: v for k, v in user_cfg.items() if k != "buckets"})
            except Exception:
                pass
            FileOps.write_file(root / "r2-config.json", json.dumps(cfg, indent=2), ctx)

            # Write r2_client.py
            FileOps.write_file(root / "r2_client.py", R2_CLIENT_PY, ctx)

            # Write README
            FileOps.write_file(root / "R2_README.md", R2_README, ctx)

            # Update metadata
            try:
                meta_path = root / "metadata.json"
                meta = {}
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta.setdefault("features", [])
                if "r2_storage" not in meta["features"]:
                    meta["features"].append("r2_storage")
                meta["r2_storage_added_at"] = datetime.utcnow().isoformat() + "Z"
                FileOps.write_file(meta_path, json.dumps(meta, indent=2), ctx)
            except Exception:
                pass

            ctx.log("R2 storage config and helpers created", {"path": str(root / "r2-config.json")})
        except Exception as e:
            try:
                ctx.error(f"R2StorageModule failed: {e}")
            except Exception:
                ctx.log(f"R2StorageModule failed: {e}")
            raise
