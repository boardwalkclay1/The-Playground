# Assistant module

This folder contains the AI assistant runtime used by the generator and backend.

Key files:
- `agent.py` — intent routing and high-level orchestration.
- `actions.py` — high-level file and project actions (create/edit/delete/move/patch).
- `file_tools.py` — low-level safe file operations.
- `run_tools.py` — controlled command execution helpers.
- `debug_tools.py` — log analysis and suggestions.
- `assistant_api.py` — HTTP/WebSocket adapter for invoking the assistant.
- `schemas.py`, `policy.py`, `audit_logger.py`, `session_manager.py`, `hooks.py` — supporting infrastructure.

Security:
- By default, destructive commands are blocked. Set `PLAYGROUND_ALLOW_UNSAFE_COMMANDS=true` only for local development.
- Audit logs are written to `assistant-audit.log` in the project root.
- Do not commit secrets. Use environment variables for credentials.

Testing:
- Run `pytest` in the repository root to execute assistant unit tests.
