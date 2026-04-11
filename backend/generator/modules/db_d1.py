# backend/generator/modules/db_d1.py
"""
Upgraded D1DatabaseModule

Improvements:
- Writes a clear D1 schema file (schema.d1.sql)
- Adds a migrations/ folder with an initial migration and a simple migration runner script
- Emits a lightweight db_client.py helper for runtime access (works with sqlite3 for local dev and
  can be adapted for Cloudflare D1 by swapping the connector)
- Writes a README explaining how to run migrations and use the client
- Uses FileOps and GenContext for safe writes and logging
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, Any

from ..base import GenContext, FileOps, GenModule


DEFAULT_SCHEMA = """-- schema.d1.sql
-- D1 / SQLite compatible schema for the generated app.
-- Add your tables below. Example users and posts tables are provided as a starting point.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY,
  author_id TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_id);
"""

INITIAL_MIGRATION = """-- migrations/0001_initial.sql
-- Initial migration created by Boardwalk Playground Studio on {ts}
-- Applies the base schema (schema.d1.sql). You can edit this migration or add new ones.

{schema}
"""

DB_CLIENT_PY = '''"""
db_client.py

Lightweight DB helper for local development and D1-compatible usage.

- For local development this uses sqlite3 and a file-based DB at ./data/app.db
- For Cloudflare D1, replace the `execute`/`fetch` implementations with the D1 binding (worker runtime)
- Provides simple helpers: init_db(), execute(), fetch_one(), fetch_all(), migrate()
"""

import os
import sqlite3
from pathlib import Path
from typing import Any, List, Tuple, Optional

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "app.db"
MIGRATIONS_DIR = ROOT / "migrations"

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_connection():
    """
    Return a sqlite3 connection for local dev.
    For Cloudflare D1, replace this with the D1 client.
    """
    _ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db(schema_sql: Optional[str] = None):
    """
    Initialize the database using schema.d1.sql or provided schema_sql string.
    """
    _ensure_data_dir()
    if schema_sql is None:
        schema_path = ROOT / "schema.d1.sql"
        if not schema_path.exists():
            raise FileNotFoundError("schema.d1.sql not found")
        schema_sql = schema_path.read_text(encoding="utf-8")
    conn = get_connection()
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

def execute(sql: str, params: Tuple = ()):
    """
    Execute a statement (INSERT/UPDATE/DELETE). Returns lastrowid for convenience.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def fetch_one(sql: str, params: Tuple = ()):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def fetch_all(sql: str, params: Tuple = ()):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def _applied_migrations(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS _migrations (id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
    cur.execute("SELECT id FROM _migrations ORDER BY id")
    return [r[0] for r in cur.fetchall()]

def migrate():
    """
    Apply SQL files in migrations/ in lexical order, recording applied migrations.
    """
    _ensure_data_dir()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS _migrations (id TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        applied = set(_applied_migrations(conn))
        migration_files = sorted([p.name for p in MIGRATIONS_DIR.glob("*.sql")])
        for m in migration_files:
            if m in applied:
                continue
            sql = (MIGRATIONS_DIR / m).read_text(encoding="utf-8")
            cur.executescript(sql)
            cur.execute("INSERT INTO _migrations (id, applied_at) VALUES (?, datetime('now'))", (m,))
            conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    # simple CLI for local dev
    import argparse
    parser = argparse.ArgumentParser(description="DB helper for generated app")
    parser.add_argument("--init", action="store_true", help="Initialize DB from schema.d1.sql")
    parser.add_argument("--migrate", action="store_true", help="Run migrations")
    args = parser.parse_args()
    if args.init:
        init_db()
        print("DB initialized at", DB_PATH)
    if args.migrate:
        migrate()
        print("Migrations applied")
'''

README = """# D1 / Database

This project includes:
- `schema.d1.sql` — the canonical schema (SQLite / D1 compatible).
- `migrations/` — SQL migration files applied in lexical order.
- `db_client.py` — a small helper for local development (sqlite3). For Cloudflare D1, adapt the client.

Quick start (local):
1. python3 -m venv .venv
2. source .venv/bin/activate
3. pip install -r requirements.txt  # ensure sqlite3 available (builtin)
4. python db_client.py --init
5. python db_client.py --migrate

Notes:
- For Cloudflare D1, replace the sqlite3-backed functions in db_client.py with D1 bindings.
- Keep migrations immutable once applied in production.
"""

class D1DatabaseModule(GenModule):
    """
    Generates schema, migrations, and DB helper files for D1-compatible databases.
    """

    def run(self, ctx: GenContext) -> None:
        root: Path = ctx.project_path
        FileOps.ensure_dir(root, ctx)

        try:
            # Write schema.d1.sql
            FileOps.write_file(root / "schema.d1.sql", DEFAULT_SCHEMA, ctx)

            # Write migrations folder and initial migration
            migrations_dir = root / "migrations"
            FileOps.ensure_dir(migrations_dir, ctx)
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            initial_sql = INITIAL_MIGRATION.format(ts=ts, schema=DEFAULT_SCHEMA)
            FileOps.write_file(migrations_dir / "0001_initial.sql", initial_sql, ctx)

            # Write db_client.py helper
            FileOps.write_file(root / "db_client.py", DB_CLIENT_PY, ctx)

            # Write README
            FileOps.write_file(root / "DB_README.md", README, ctx)

            # Update metadata
            try:
                meta_path = root / "metadata.json"
                meta = {}
                if meta_path.exists():
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta.setdefault("features", [])
                if "d1_schema" not in meta["features"]:
                    meta["features"].append("d1_schema")
                meta["d1_schema_added_at"] = datetime.utcnow().isoformat() + "Z"
                FileOps.write_file(meta_path, json.dumps(meta, indent=2), ctx)
            except Exception:
                pass

            ctx.log("D1 schema and DB helpers created", {"path": str(root)})
        except Exception as e:
            try:
                ctx.error(f"D1DatabaseModule failed: {e}")
            except Exception:
                ctx.log(f"D1DatabaseModule failed: {e}")
            raise
