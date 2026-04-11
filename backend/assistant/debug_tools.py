# backend/assistant/debug_tools.py
"""
Upgraded DebugTools

Improvements:
- Reads multiple common log files (debug.log, error.log, logs/*.log) and aggregates content
- Parses stack traces and extracts exception types, messages, file paths and line numbers
- Attempts lightweight static checks: looks for SyntaxError via ast.parse on .py files referenced
- Gathers file context (surrounding lines) for referenced files/lines
- Produces actionable suggestions for common exception types (NameError, ImportError, SyntaxError, TypeError, KeyError, FileNotFoundError)
- Writes a machine-readable debug report (debug-report.json) into the project root and appends an audit entry to assistant-audit.log
- Safe path handling to avoid escaping the project directory
- Returns a structured dict with findings, suggestions, and raw logs for UI consumption
"""

from pathlib import Path
import re
import json
import ast
import time
from typing import Dict, Any, List, Optional

AUDIT_FILENAME = "assistant-audit.log"
REPORT_FILENAME = "debug-report.json"
LOG_GLOBS = ["debug.log", "error.log", "logs/*.log", "*.log"]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_project_root(project_path: str) -> Path:
    p = Path(project_path).resolve()
    return p


def _is_within(root: Path, target: Path) -> bool:
    try:
        return str(target.resolve()).startswith(str(root.resolve()))
    except Exception:
        return False


def _read_logs(root: Path) -> Dict[str, str]:
    logs: Dict[str, str] = {}
    for pattern in LOG_GLOBS:
        for p in sorted(root.glob(pattern)):
            if p.is_file() and _is_within(root, p):
                try:
                    logs[str(p.relative_to(root))] = p.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    logs[str(p.relative_to(root))] = "<unreadable>"
    return logs


_STACK_TRACE_RE = re.compile(
    r'(?P<file>File "?(?P<path>[^",\n]+)"?, line (?P<line>\d+), in (?P<func>[^\n]+))|(?P<pyexc>Traceback \(most recent call last\):)'
)


EXCEPTION_LINE_RE = re.compile(r'^(?P<type>[A-Za-z_][A-Za-z0-9_.]+):\s*(?P<msg>.*)$')


def _extract_stack_traces(text: str) -> List[Dict[str, Any]]:
    """
    Extracts stack trace blocks and returns a list of traces with frames and exception line.
    """
    traces: List[Dict[str, Any]] = []
    # Split by common Python traceback header
    parts = re.split(r'(Traceback \(most recent call last\):)', text)
    if len(parts) <= 1:
        # fallback: try to find exception lines and surrounding context
        for m in EXCEPTION_LINE_RE.finditer(text):
            traces.append({"frames": [], "exception": {"type": m.group("type"), "message": m.group("msg")}, "raw": text})
        return traces

    # Reconstruct blocks: parts like ['', 'Traceback...', rest, 'Traceback...', rest...]
    joined = "".join(parts)
    # Find all traceback blocks by looking for "Traceback" up to next blank line followed by exception
    tb_blocks = re.findall(r'Traceback \(most recent call last\):[\s\S]*?(?:\n[A-Za-z_][A-Za-z0-9_.]+: .+)', text)
    for block in tb_blocks:
        frames = []
        for m in re.finditer(r'  File "([^"]+)", line (\d+), in ([^\n]+)\n\s+(?P<code>.+)', block):
            frames.append({"path": m.group(1), "line": int(m.group(2)), "func": m.group(3).strip(), "code": m.group("code").strip()})
        # exception line is last non-empty line
        exc_lines = [ln for ln in block.splitlines() if ln.strip()]
        exc_line = exc_lines[-1] if exc_lines else ""
        em = EXCEPTION_LINE_RE.match(exc_line)
        exc = {"type": None, "message": exc_line}
        if em:
            exc = {"type": em.group("type"), "message": em.group("msg")}
        traces.append({"frames": frames, "exception": exc, "raw": block})
    return traces


def _gather_file_context(root: Path, rel_path: str, line_no: int, context: int = 3) -> Dict[str, Any]:
    """
    Return surrounding lines for a file and line number. If file not found, return empty.
    """
    try:
        candidate = (root / rel_path).resolve()
        if not _is_within(root, candidate) or not candidate.exists():
            return {"found": False, "path": rel_path}
        lines = candidate.read_text(encoding="utf-8", errors="replace").splitlines()
        idx = max(0, line_no - 1)
        start = max(0, idx - context)
        end = min(len(lines), idx + context + 1)
        excerpt = lines[start:end]
        return {
            "found": True,
            "path": str(candidate.relative_to(root)),
            "line": line_no,
            "context_start": start + 1,
            "context_end": end,
            "excerpt": "\n".join(excerpt),
        }
    except Exception:
        return {"found": False, "path": rel_path}


def _suggest_for_exception(exc_type: Optional[str], message: str) -> List[str]:
    """
    Provide heuristic suggestions for common Python exceptions.
    """
    suggestions: List[str] = []
    t = (exc_type or "").split(".")[-1] if exc_type else ""
    msg = (message or "").lower()

    if t == "NameError" or "nameerror" in msg:
        suggestions.append("Check for misspelled variable or function names. Ensure the name is defined before use.")
        suggestions.append("If the name should come from an import, verify the import statement and module path.")
    if t == "ImportError" or "importerror" in msg or "no module named" in msg:
        suggestions.append("Verify the module/package is installed and available in the environment.")
        suggestions.append("Check for relative vs absolute import issues and correct package structure.")
    if t == "SyntaxError" or "syntaxerror" in msg:
        suggestions.append("Open the referenced file and inspect the indicated line for missing colons, parentheses, or indentation issues.")
        suggestions.append("Run `python -m py_compile <file>` locally to get a precise syntax error location.")
    if t == "TypeError" or "typeerror" in msg:
        suggestions.append("Check the types of arguments passed to the function. Add defensive type checks or convert types as needed.")
    if t == "KeyError" or "keyerror" in msg:
        suggestions.append("Ensure the dictionary key exists before access or use dict.get(key, default).")
    if t == "FileNotFoundError" or "filenotfounderror" in msg:
        suggestions.append("Verify the file path is correct and that the file exists. Consider using Path.exists() before opening.")
    if "permission denied" in msg:
        suggestions.append("Check file permissions and the user the process runs as. Adjust permissions or run as a different user.")
    if not suggestions:
        suggestions.append("Inspect the stack trace and referenced files. Consider running tests or adding logging around the failing area.")
    return suggestions


def _static_syntax_check(root: Path, rel_path: str) -> Dict[str, Any]:
    """
    Attempt to parse a Python file to detect SyntaxError without executing it.
    """
    try:
        candidate = (root / rel_path).resolve()
        if not _is_within(root, candidate) or not candidate.exists():
            return {"checked": False, "path": rel_path, "error": "file not found"}
        text = candidate.read_text(encoding="utf-8", errors="replace")
        try:
            ast.parse(text)
            return {"checked": True, "path": str(candidate.relative_to(root)), "syntax_ok": True}
        except SyntaxError as se:
            return {
                "checked": True,
                "path": str(candidate.relative_to(root)),
                "syntax_ok": False,
                "syntax_error": {"msg": str(se), "lineno": se.lineno, "offset": se.offset, "text": se.text},
            }
    except Exception as e:
        return {"checked": False, "path": rel_path, "error": str(e)}


class DebugTools:
    """
    Reads logs, analyzes errors, and proposes fixes.
    """

    def __init__(self):
        # placeholder for future configuration
        self.name = "DebugTools"

    def _append_audit(self, project_root: Path, entry: Dict[str, Any]) -> None:
        try:
            log_path = project_root / AUDIT_FILENAME
            entry = dict(entry)
            entry.setdefault("timestamp", _now_iso())
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def debug_project(self, prompt: str, project_path: str) -> Dict[str, Any]:
        """
        Analyze project logs and source files to produce a debug report.

        Returns a dict:
        {
          "success": bool,
          "report_path": "debug-report.json",
          "findings": [...],
          "suggestions": [...],
          "logs": { "debug.log": "..." },
          "raw": { ... }  # optional raw data for UI
        }
        """
        try:
            root = _safe_project_root(project_path)
            if not root.exists() or not root.is_dir():
                return {"success": False, "error": "Project not found."}

            logs = _read_logs(root)
            aggregated_text = "\n\n".join(logs.values()) if logs else ""

            findings: List[Dict[str, Any]] = []
            suggestions: List[str] = []

            # Extract stack traces
            traces = _extract_stack_traces(aggregated_text)
            if traces:
                for t in traces:
                    exc = t.get("exception", {})
                    exc_type = exc.get("type")
                    exc_msg = exc.get("message", "")
                    frames = t.get("frames", [])
                    trace_entry = {"exception": exc, "frames": [], "raw": t.get("raw", "")}
                    # For each frame, gather context if possible
                    for f in frames:
                        path = f.get("path")
                        line = f.get("line", 0)
                        ctx = _gather_file_context(root, path, line, context=4)
                        trace_entry["frames"].append({"path": path, "line": line, "func": f.get("func"), "code": f.get("code"), "context": ctx})
                        # static check for python files
                        if path.endswith(".py"):
                            syntax = _static_syntax_check(root, path)
                            if syntax.get("syntax_ok") is False:
                                trace_entry.setdefault("syntax_issues", []).append(syntax)
                    findings.append(trace_entry)
                    # suggestions for this exception
                    s = _suggest_for_exception(exc_type, exc_msg)
                    suggestions.extend(s)
            else:
                # No explicit traces found: attempt to find common exception lines
                for name, content in logs.items():
                    for m in EXCEPTION_LINE_RE.finditer(content):
                        exc_type = m.group("type")
                        exc_msg = m.group("msg")
                        findings.append({"exception": {"type": exc_type, "message": exc_msg}, "frames": []})
                        suggestions.extend(_suggest_for_exception(exc_type, exc_msg))

            # If no findings at all, attempt to run quick static checks on top-level python files
            if not findings:
                py_files = sorted([p.relative_to(root).as_posix() for p in root.rglob("*.py") if _is_within(root, p)])
                static_results = []
                for rel in py_files:
                    res = _static_syntax_check(root, rel)
                    static_results.append(res)
                    if res.get("syntax_ok") is False:
                        suggestions.append(f"Syntax error in {res.get('path')}: {res.get('syntax_error')}")
                if static_results:
                    findings.append({"static_checks": static_results})

            # Deduplicate suggestions and trim
            unique_suggestions = []
            seen = set()
            for s in suggestions:
                if s not in seen:
                    unique_suggestions.append(s)
                    seen.add(s)
            suggestions = unique_suggestions[:20]

            # Build report
            report = {
                "project": str(root),
                "generated_at": _now_iso(),
                "prompt": prompt,
                "findings": findings,
                "suggestions": suggestions,
                "log_files": list(logs.keys()),
            }

            # Write report to project root
            try:
                report_path = root / REPORT_FILENAME
                report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            except Exception:
                report_path = None

            # Append audit entry
            try:
                self._append_audit(root, {"action": "debug_project", "report": str(report_path.name) if report_path else None, "summary": f"{len(findings)} findings"})
            except Exception:
                pass

            return {
                "success": True,
                "report_path": str(report_path.relative_to(root)) if report_path else None,
                "findings_count": len(findings),
                "findings": findings,
                "suggestions": suggestions,
                "logs": logs,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
