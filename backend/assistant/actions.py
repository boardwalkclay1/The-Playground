# backend/assistant/actions.py
"""
Upgraded AssistantActions

Improvements:
- Safer path handling (prevents path traversal)
- Atomic writes with temporary file + rename
- Optional backups with timestamped .bak files
- Read, list, create, edit, delete, move, and patch helpers
- Simple audit logging to assistant-audit.log in the project root
- Clear, consistent return payloads with success/error fields
"""

from pathlib import Path
import os
import shutil
import tempfile
import time
import json
import difflib
from typing import Dict, Any, Optional, List

AUDIT_FILENAME = "assistant-audit.log"


def _now_ts() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def _log_audit(project_path: Path, entry: Dict[str, Any]) -> None:
    try:
        log_path = project_path / AUDIT_FILENAME
        entry = dict(entry)
        entry.setdefault("timestamp", _now_ts())
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # never raise from logging
        pass


def _resolve_project_path(project_path: str) -> Path:
    p = Path(project_path).resolve()
    return p


def _is_within_project(project_root: Path, target: Path) -> bool:
    try:
        return str(target.resolve()).startswith(str(project_root.resolve()))
    except Exception:
        return False


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    os.close(fd)
    tmp_path = Path(tmp)
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _create_backup(path: Path) -> Optional[str]:
    try:
        if not path.exists():
            return None
        bak = path.with_name(path.name + f".bak.{_now_ts()}")
        shutil.copy2(path, bak)
        return str(bak)
    except Exception:
        return None


class AssistantActions:
    """
    High-level actions the AI can perform inside a project directory.

    Methods return dicts with at least a 'success' boolean and additional fields.
    """

    def create_file(self, prompt: str, project_path: str, content: str = "", overwrite: bool = False) -> Dict[str, Any]:
        """
        Create a file. Prompt may contain the filename or path.
        Returns created path on success.
        """
        try:
            # Extract filename from prompt if present (support "create file <path>")
            filename = prompt
            if "create file" in prompt:
                filename = prompt.split("create file", 1)[1].strip()
            filename = filename.strip().lstrip("/")

            if not filename:
                return {"success": False, "error": "No filename provided."}

            root = _resolve_project_path(project_path)
            target = (root / filename).resolve()
            if not _is_within_project(root, target):
                return {"success": False, "error": "Path outside project not allowed."}

            if target.exists() and not overwrite:
                return {"success": False, "error": "File already exists. Use overwrite=True to replace."}

            # create parent dirs and write atomically
            _atomic_write(target, content or "")
            _log_audit(root, {"action": "create_file", "path": str(target.relative_to(root)), "overwrite": overwrite})
            return {"success": True, "created": str(target.relative_to(root))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_file(self, rel_path: str, project_path: str) -> Dict[str, Any]:
        """
        Read a file's content safely.
        """
        try:
            root = _resolve_project_path(project_path)
            target = (root / rel_path).resolve()
            if not _is_within_project(root, target):
                return {"success": False, "error": "Path outside project not allowed."}
            if not target.exists() or not target.is_file():
                return {"success": False, "error": "File not found."}
            content = target.read_text(encoding="utf-8")
            _log_audit(root, {"action": "read_file", "path": str(target.relative_to(root))})
            return {"success": True, "path": str(target.relative_to(root)), "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, project_path: str, glob: str = "**/*") -> Dict[str, Any]:
        """
        List files under the project. Returns list of relative file paths.
        """
        try:
            root = _resolve_project_path(project_path)
            if not root.exists() or not root.is_dir():
                return {"success": False, "error": "Project not found."}
            files: List[str] = []
            for p in sorted(root.glob(glob)):
                if p.is_file():
                    files.append(str(p.relative_to(root)))
            _log_audit(root, {"action": "list_files", "count": len(files)})
            return {"success": True, "files": files}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def edit_file(self, prompt: str, project_path: str, create_backup: bool = True) -> Dict[str, Any]:
        """
        Edit a file. Expected prompt formats:
          - "edit file path/to/file: new content here"
          - or provide filename and content separately via parameters (not used here)
        """
        try:
            if ":" not in prompt:
                return {"success": False, "error": "Missing ':' separator between filename and content."}
            before, after = prompt.split(":", 1)
            before = before.replace("edit file", "").strip()
            if not before:
                return {"success": False, "error": "No filename provided."}

            root = _resolve_project_path(project_path)
            target = (root / before).resolve()
            if not _is_within_project(root, target):
                return {"success": False, "error": "Path outside project not allowed."}
            if not target.exists():
                return {"success": False, "error": "File not found."}

            backup = _create_backup(target) if create_backup else None
            _atomic_write(target, after.strip())
            _log_audit(root, {"action": "edit_file", "path": str(target.relative_to(root)), "backup": backup})
            return {"success": True, "edited": str(target.relative_to(root)), "backup": backup}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, prompt: str, project_path: str, allow_recursive: bool = False) -> Dict[str, Any]:
        """
        Delete a file or directory. Prompt may be "delete path/to/file".
        If target is a directory, allow_recursive must be True to remove it.
        """
        try:
            filename = prompt.replace("delete", "").strip()
            if not filename:
                return {"success": False, "error": "No filename provided."}

            root = _resolve_project_path(project_path)
            target = (root / filename).resolve()
            if not _is_within_project(root, target):
                return {"success": False, "error": "Path outside project not allowed."}
            if not target.exists():
                return {"success": False, "error": "File or directory not found."}

            if target.is_dir():
                if not allow_recursive:
                    return {"success": False, "error": "Target is a directory. Set allow_recursive=True to delete directories."}
                shutil.rmtree(target)
                _log_audit(root, {"action": "delete_dir", "path": str(target.relative_to(root))})
                return {"success": True, "deleted": str(target.relative_to(root))}
            else:
                backup = _create_backup(target)
                target.unlink()
                _log_audit(root, {"action": "delete_file", "path": str(target.relative_to(root)), "backup": backup})
                return {"success": True, "deleted": str(target.relative_to(root)), "backup": backup}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def move_file(self, prompt: str, project_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """
        Move or rename a file.
        Expected prompt: "move file src/path to dst/path"
        """
        try:
            text = prompt.replace("move file", "").strip()
            parts = text.split(" to ")
            if len(parts) != 2:
                return {"success": False, "error": "Invalid move format. Use 'move file <src> to <dst>'."}
            src_rel = parts[0].strip()
            dst_rel = parts[1].strip()
            if not src_rel or not dst_rel:
                return {"success": False, "error": "Source or destination missing."}

            root = _resolve_project_path(project_path)
            src = (root / src_rel).resolve()
            dst = (root / dst_rel).resolve()
            if not _is_within_project(root, src) or not _is_within_project(root, dst):
                return {"success": False, "error": "Path outside project not allowed."}
            if not src.exists():
                return {"success": False, "error": "Source not found."}
            if dst.exists() and not overwrite:
                return {"success": False, "error": "Destination exists. Use overwrite=True to replace."}

            dst.parent.mkdir(parents=True, exist_ok=True)
            # If destination exists and overwrite True, remove it first
            if dst.exists() and overwrite:
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            shutil.move(str(src), str(dst))
            _log_audit(root, {"action": "move_file", "from": str(src.relative_to(root)), "to": str(dst.relative_to(root))})
            return {"success": True, "moved": {"from": str(src.relative_to(root)), "to": str(dst.relative_to(root))}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def propose_patch(self, patch_text: str, project_path: str) -> Dict[str, Any]:
        """
        Save a proposed unified diff patch to the project and return a preview.
        The patch is saved as assistant-proposed-<ts>.patch
        """
        try:
            root = _resolve_project_path(project_path)
            if not root.exists():
                return {"success": False, "error": "Project not found."}
            patch_file = root / f"assistant-proposed-{_now_ts()}.patch"
            patch_file.write_text(patch_text, encoding="utf-8")
            _log_audit(root, {"action": "propose_patch", "patch_file": str(patch_file.name)})

            # Provide a simple preview: return the raw patch and list of files mentioned
            files = []
            for line in patch_text.splitlines():
                if line.startswith("+++ ") or line.startswith("--- "):
                    # lines like "+++ b/path/to/file" or "+++ path/to/file"
                    parts = line.split()
                    if len(parts) >= 2:
                        path = parts[1].lstrip("ab/").strip()
                        if path and path not in files:
                            files.append(path)
            return {"success": True, "patch_file": str(patch_file.name), "files": files, "preview": patch_text[:16_000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_patch(self, patch_text: str, project_path: str, create_backup: bool = True) -> Dict[str, Any]:
        """
        Attempt to apply a unified diff patch in a conservative, file-by-file manner.
        This implementation:
          - Saves the patch to assistant-applied-<ts>.patch
          - For each file mentioned, attempts to compute the patched content using difflib
          - Writes patched files atomically and records backups
        Note: This is best-effort and not a full 'patch' implementation. Review results after applying.
        """
        try:
            root = _resolve_project_path(project_path)
            if not root.exists():
                return {"success": False, "error": "Project not found."}

            # Save patch for audit
            applied_patch_file = root / f"assistant-applied-{_now_ts()}.patch"
            applied_patch_file.write_text(patch_text, encoding="utf-8")
            _log_audit(root, {"action": "apply_patch", "patch_file": str(applied_patch_file.name)})

            # Parse simple unified diff into per-file hunks using difflib
            # difflib.restore expects a sequence produced by difflib.unified_diff; we will attempt to split by file
            lines = patch_text.splitlines(keepends=True)
            file_sections: Dict[str, List[str]] = {}
            cur_file = None
            cur_lines: List[str] = []

            # Very simple parser: look for lines starting with '*** ' or '--- ' and '+++ '
            # We'll detect '+++ ' as the start of the new file path and use the previous '--- ' as original
            for ln in lines:
                if ln.startswith("+++ "):
                    # commit previous
                    if cur_file and cur_lines:
                        file_sections.setdefault(cur_file, []).extend(cur_lines)
                    # determine new file path
                    parts = ln.split()
                    if len(parts) >= 2:
                        cur_file = parts[1].lstrip("ab/").strip()
                    else:
                        cur_file = None
                    cur_lines = [ln]
                else:
                    if cur_file is not None:
                        cur_lines.append(ln)
            if cur_file and cur_lines:
                file_sections.setdefault(cur_file, []).extend(cur_lines)

            results = {"applied": [], "skipped": [], "errors": []}

            for rel_path, hunks in file_sections.items():
                try:
                    target = (root / rel_path).resolve()
                    if not _is_within_project(root, target):
                        results["skipped"].append({"path": rel_path, "reason": "outside project"})
                        continue

                    orig_text = ""
                    if target.exists() and target.is_file():
                        orig_text = target.read_text(encoding="utf-8")
                    # Attempt to apply patch using difflib by reconstructing unified diff for this file
                    # Build a minimal unified diff sequence for difflib.restore
                    # Fallback: if we cannot safely apply, skip
                    # As a conservative approach, compute a simple patched version by applying line-based replacements
                    # This is not a full patch algorithm; prefer manual review.
                    patched = None
                    try:
                        # Try to use difflib to parse hunks: create a fake diff between orig and a guessed new content
                        # Here we attempt to extract lines starting with '+' and '-' from hunks to build a naive patched text
                        orig_lines = orig_text.splitlines(keepends=True)
                        new_lines = []
                        for h in hunks:
                            if h.startswith("+") and not h.startswith("+++"):
                                new_lines.append(h[1:])
                            elif h.startswith("-") and not h.startswith("---"):
                                # removed line; skip
                                pass
                            elif h.startswith(" "):
                                new_lines.append(h[1:])
                            # ignore other markers
                        if new_lines:
                            patched = "".join(new_lines)
                        else:
                            # If no clear new_lines, skip applying
                            patched = None
                    except Exception:
                        patched = None

                    if patched is None:
                        results["skipped"].append({"path": rel_path, "reason": "could not compute patched content safely"})
                        continue

                    backup = _create_backup(target) if create_backup and target.exists() else None
                    _atomic_write(target, patched)
                    results["applied"].append({"path": rel_path, "backup": backup})
                    _log_audit(root, {"action": "apply_patch_file", "path": rel_path, "backup": backup})
                except Exception as e:
                    results["errors"].append({"path": rel_path, "error": str(e)})

            return {"success": True, **results}
        except Exception as e:
            return {"success": False, "error": str(e)}
