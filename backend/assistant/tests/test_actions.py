# backend/assistant/tests/test_actions.py
import tempfile
import shutil
from pathlib import Path
import pytest
from unittest.mock import patch

from backend.assistant.actions import AssistantActions


@pytest.fixture
def tmp_project():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d)


# ============================================================
# BASIC FILE OPS
# ============================================================

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
    backups = list(tmp_project.glob("a.txt.bak.*"))
    assert backups

def test_move_file(tmp_project):
    a = AssistantActions()
    src = tmp_project / "src.txt"
    src.write_text("x")
    res = a.move_file("move file src.txt to nested/dst.txt", str(tmp_project))
    assert res["success"]
    assert (tmp_project / "nested" / "dst.txt").exists()


# ============================================================
# DELETE
# ============================================================

def test_delete_file(tmp_project):
    a = AssistantActions()
    p = tmp_project / "del.txt"
    p.write_text("bye")
    res = a.delete_file("delete del.txt", str(tmp_project))
    assert res["success"]
    assert not p.exists()

def test_delete_directory_recursive(tmp_project):
    a = AssistantActions()
    d = tmp_project / "folder"
    d.mkdir()
    (d / "x.txt").write_text("x")
    res = a.delete_file("delete folder", str(tmp_project), allow_recursive=True)
    assert res["success"]
    assert not d.exists()


# ============================================================
# LIST FILES
# ============================================================

def test_list_files(tmp_project):
    a = AssistantActions()
    (tmp_project / "one.txt").write_text("1")
    (tmp_project / "two.txt").write_text("2")
    res = a.list_files(str(tmp_project))
    assert res["success"]
    assert "one.txt" in res["files"]
    assert "two.txt" in res["files"]


# ============================================================
# PATCH ENGINE
# ============================================================

def test_propose_patch(tmp_project):
    a = AssistantActions()
    patch = """--- a.txt
+++ a.txt
@@
-old
+new
"""
    res = a.propose_patch(patch, str(tmp_project))
    assert res["success"]
    assert "patch_file" in res

def test_apply_patch(tmp_project):
    a = AssistantActions()
    p = tmp_project / "a.txt"
    p.write_text("old\n")
    patch = """--- a.txt
+++ a.txt
@@
-old
+new
"""
    res = a.apply_patch(patch, str(tmp_project))
    assert res["success"]
    assert "applied" in res
    assert p.read_text().strip() == "new"


# ============================================================
# PYTHON TOOLS
# ============================================================

def test_python_generate_and_explain(tmp_project):
    a = AssistantActions()
    res = a.python_generate(str(tmp_project), "script.py", "test script")
    assert res["success"]

    res2 = a.python_explain("script.py", str(tmp_project))
    assert res2["success"]
    assert "Generated file" in res2["content"]

def test_python_run(tmp_project):
    a = AssistantActions()
    (tmp_project / "runme.py").write_text('print("OK")')
    res = a.python_run("runme.py", str(tmp_project))
    assert res["success"]
    assert "OK" in res["stdout"]


# ============================================================
# GIT CLONE (MOCKED)
# ============================================================

@patch("subprocess.check_call")
def test_git_clone(mock_call, tmp_project):
    a = AssistantActions()
    res = a.git_clone(str(tmp_project), "https://example.com/repo.git", "repo")
    assert res["success"]
    mock_call.assert_called_once()


# ============================================================
# REPO ANALYZER + REPO UI
# ============================================================

def test_analyze_repo(tmp_project):
    a = AssistantActions()
    folder = tmp_project / "repo"
    folder.mkdir()
    (folder / "main.py").write_text("print('x')")
    res = a.analyze_repo(str(tmp_project), "repo")
    assert res["success"]
    assert res["meta"]["has_python"]

def test_build_repo_ui(tmp_project):
    a = AssistantActions()
    folder = tmp_project / "repo"
    folder.mkdir()
    (folder / "main.py").write_text("print('x')")
    res = a.build_repo_ui(str(tmp_project), "repo")
    assert res["success"]
    assert "panels" in res


# ============================================================
# USB TOOLS (MOCKED)
# ============================================================

def test_usb_list(tmp_project):
    a = AssistantActions()
    res = a.usb_list()
    assert res["success"]
    assert "mounts" in res

@patch("shutil.copytree")
def test_usb_export(mock_copy, tmp_project):
    a = AssistantActions()
    folder = tmp_project / "data"
    folder.mkdir()
    (folder / "x.txt").write_text("x")
    res = a.usb_export(str(tmp_project), "data", "/tmp")
    assert res["success"]
    mock_copy.assert_called_once()
