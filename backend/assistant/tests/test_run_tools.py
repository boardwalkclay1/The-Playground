# backend/assistant/tests/test_run_tools.py
import tempfile
import shutil
from pathlib import Path
from backend.assistant.run_tools import RunTools

def test_run_command_echo(tmp_project := Path(tempfile.mkdtemp())):
    try:
        rt = RunTools()
        # create a simple script
        p = tmp_project / "script.sh"
        p.write_text("#!/bin/sh\necho hello\n", encoding="utf-8")
        import os
        os.chmod(p, 0o755)
        res = rt.run_command(str(p), str(tmp_project), timeout=5)
        assert res["success"]
    finally:
        shutil.rmtree(tmp_project)
