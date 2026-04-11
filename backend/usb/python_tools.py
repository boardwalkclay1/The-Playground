# backend/assistant/python_tools.py
from pathlib import Path
import subprocess
import textwrap

def explain_python(file_path: str) -> str:
    """
    Very simple: returns the file content; your LLM layer will do the 'explain'.
    """
    p = Path(file_path)
    if not p.exists():
        return f"File not found: {file_path}"
    return p.read_text(encoding="utf-8")

def generate_python_file(target_dir: str, file_name: str, description: str) -> str:
    """
    Stub: create a Python file with a docstring containing the description.
    Your LLM can later refine this.
    """
    base = Path(target_dir)
    base.mkdir(parents=True, exist_ok=True)
    target = base / file_name

    content = textwrap.dedent(f'''
    """
    {description}
    """

    def main():
        print("Generated Python file: {file_name}")

    if __name__ == "__main__":
        main()
    ''').strip() + "\n"

    target.write_text(content, encoding="utf-8")
    return str(target)

def run_python(file_path: str, cwd: str | None = None) -> dict:
    """
    Run a Python file and capture stdout/stderr.
    """
    cmd = ["python3", file_path]
    proc = subprocess.Popen(
        cmd,
        cwd=cwd or None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = proc.communicate()
    return {
        "returncode": proc.returncode,
        "stdout": out,
        "stderr": err,
    }
