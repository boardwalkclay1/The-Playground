# backend/assistant/tests/test_actions.py
import tempfile
import shutil
from pathlib import Path
import pytest
from backend.assistant.actions import AssistantActions

@pytest.fixture
def tmp_project():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d)

def test_create_and_read_file(tmp_project):
    a = AssistantActions()
    res = a.create_file("create file hello.txt", str(tmp_project), content="hi", overwrite=True)
    assert res["success"]
    p = tmp_project / "hello.txt"
    assert p.exists()
    assert p.read_text() == "hi"

def test_edit_file_backup(tmp_project):
    a = AssistantActions()
    p = tmp_project / "a.txt"
    p.write_text("old")
    res = a.edit_file("edit file a.txt: new content", str(tmp_project))
    assert res["success"]
    assert p.read_text() == "new content"
    # backup exists
    backups = list(tmp_project.glob("a.txt.bak.*"))
    assert backups

def test_move_file(tmp_project):
    a = AssistantActions()
    src = tmp_project / "src.txt"
    src.write_text("x")
    res = a.move_file("move file src.txt to nested/dst.txt", str(tmp_project))
    assert res["success"]
    assert (tmp_project / "nested" / "dst.txt").exists()
