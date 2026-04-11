# backend/assistant/tests/test_run_tools.py
import tempfile
import shutil
from pathlib import Path
import pytest
import asyncio

from backend.assistant.run_tools import RunTools


@pytest.fixture
def tmp_project():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d)


# ============================================================
# BASIC run_command
# ============================================================

def test_run_command_echo(tmp_project):
    rt = RunTools()

    script = tmp_project / "script.sh"
    script.write_text("#!/bin/sh\necho hello\n", encoding="utf-8")

    import os
    os.chmod(script, 0o755)

    res = rt.run_command(str(script), str(tmp_project), timeout=5)
    assert res["success"]
    assert "hello" in res.get("stdout", "")


# ============================================================
# run_command: stderr capture
# ============================================================

def test_run_command_stderr(tmp_project):
    rt = RunTools()

    script = tmp_project / "err.sh"
    script.write_text("#!/bin/sh\necho error >&2\nexit 1\n", encoding="utf-8")

    import os
    os.chmod(script, 0o755)

    res = rt.run_command(str(script), str(tmp_project), timeout=5)
    assert not res["success"]
    assert "error" in res.get("stderr", "")


# ============================================================
# run_command: timeout
# ============================================================

def test_run_command_timeout(tmp_project):
    rt = RunTools()

    script = tmp_project / "sleep.sh"
    script.write_text("#!/bin/sh\nsleep 10\necho done\n", encoding="utf-8")

    import os
    os.chmod(script, 0o755)

    res = rt.run_command(str(script), str(tmp_project), timeout=1)
    assert not res["success"]
    assert "timeout" in res.get("error", "").lower()


# ============================================================
# stream_command
# ============================================================

@pytest.mark.asyncio
async def test_stream_command(tmp_project):
    rt = RunTools()

    script = tmp_project / "stream.sh"
    script.write_text("#!/bin/sh\necho line1\necho line2\n", encoding="utf-8")

    import os
    os.chmod(script, 0o755)

    outputs = []
    async for chunk in rt.stream_command(str(script), str(tmp_project), timeout=5):
        outputs.append(chunk)

    assert len(outputs) >= 2
    assert any("line1" in c.get("stdout", "") for c in outputs)
    assert any("line2" in c.get("stdout", "") for c in outputs)


# ============================================================
# Working directory safety
# ============================================================

def test_run_command_respects_cwd(tmp_project):
    rt = RunTools()

    script = tmp_project / "pwd.sh"
    script.write_text("#!/bin/sh\npwd\n", encoding="utf-8")

    import os
    os.chmod(script, 0o755)

    res = rt.run_command(str(script), str(tmp_project), timeout=5)
    assert res["success"]
    assert str(tmp_project) in res.get("stdout", "")
