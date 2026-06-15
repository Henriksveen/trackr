"""End-to-end CLI tests using Typer's CliRunner.

Each test runs in an isolated temp cwd (see conftest). We assert on exit
codes and on the persisted state file rather than parsing colored Rich
output where possible.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from trackr.storage import STATE_FILENAME, STORE_DIRNAME


def _state(root: Path) -> dict:
    return json.loads((root / STORE_DIRNAME / STATE_FILENAME).read_text())


def _ids(root: Path) -> list[str]:
    return [t["id"] for t in _state(root)["tasks"]]


def _first_id(root: Path) -> str:
    return _ids(root)[0]


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------
class TestInit:
    def test_creates_store(self, invoke, workdir: Path) -> None:
        result = invoke("init")
        assert result.exit_code == 0
        assert (workdir / STORE_DIRNAME / STATE_FILENAME).is_file()
        assert "Initialized" in result.stdout

    def test_rerun_is_graceful(self, invoke, workdir: Path) -> None:
        invoke("init")
        result = invoke("init")
        assert result.exit_code == 0
        assert "Already" in result.stdout


# --------------------------------------------------------------------------
# guard: commands before init
# --------------------------------------------------------------------------
class TestRequiresInit:
    def test_add_before_init_fails(self, invoke, workdir: Path) -> None:
        result = invoke("add", "x")
        assert result.exit_code == 1
        assert "Not a trackr repository" in result.output

    def test_list_before_init_fails(self, invoke, workdir: Path) -> None:
        assert invoke("list").exit_code == 1


# --------------------------------------------------------------------------
# add
# --------------------------------------------------------------------------
class TestAdd:
    def test_add_persists_task(self, invoke, initialized: Path) -> None:
        result = invoke("add", "Write tests")
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        assert len(tasks) == 1
        assert tasks[0]["description"] == "Write tests"
        assert tasks[0]["status"] == "Todo"
        assert re.fullmatch(r"[0-9a-f]{4}", tasks[0]["id"])

    def test_description_is_trimmed(self, invoke, initialized: Path) -> None:
        invoke("add", "   spaced   ")
        assert _state(initialized)["tasks"][0]["description"] == "spaced"

    def test_empty_description_rejected(self, invoke, initialized: Path) -> None:
        result = invoke("add", "   ")
        assert result.exit_code == 1
        assert "empty" in result.output.lower()
        assert _state(initialized)["tasks"] == []

    def test_ids_are_unique(self, invoke, initialized: Path) -> None:
        for i in range(10):
            invoke("add", f"task {i}")
        ids = _ids(initialized)
        assert len(ids) == len(set(ids)) == 10


# --------------------------------------------------------------------------
# list
# --------------------------------------------------------------------------
class TestList:
    def test_empty_message(self, invoke, initialized: Path) -> None:
        result = invoke("list")
        assert result.exit_code == 0
        assert "No tasks yet" in result.output

    def test_hides_done_by_default(self, invoke, initialized: Path) -> None:
        invoke("add", "keep me visible")
        invoke("add", "finish me")
        done_id = _ids(initialized)[1]
        invoke("status", done_id, "done")

        result = invoke("list")
        assert "keep me visible" in result.output
        assert "finish me" not in result.output

    def test_all_flag_shows_done(self, invoke, initialized: Path) -> None:
        invoke("add", "finish me")
        done_id = _first_id(initialized)
        invoke("status", done_id, "done")

        result = invoke("list", "--all")
        assert "finish me" in result.output

    def test_all_only_done_default_hint(self, invoke, initialized: Path) -> None:
        invoke("add", "finish me")
        invoke("status", _first_id(initialized), "done")
        result = invoke("list")
        # nothing open -> hint to use --all
        assert "--all" in result.output


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------
class TestStatus:
    def test_update_persists(self, invoke, initialized: Path) -> None:
        invoke("add", "task")
        tid = _first_id(initialized)
        result = invoke("status", tid, "wip")
        assert result.exit_code == 0
        assert _state(initialized)["tasks"][0]["status"] == "In Progress"

    def test_case_insensitive_id(self, invoke, initialized: Path) -> None:
        invoke("add", "task")
        tid = _first_id(initialized).upper()
        assert invoke("status", tid, "done").exit_code == 0
        assert _state(initialized)["tasks"][0]["status"] == "Done"

    def test_noop_when_same(self, invoke, initialized: Path) -> None:
        invoke("add", "task")
        tid = _first_id(initialized)
        result = invoke("status", tid, "todo")
        assert result.exit_code == 0
        assert "already" in result.output.lower()

    def test_invalid_status_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "task")
        tid = _first_id(initialized)
        result = invoke("status", tid, "banana")
        assert result.exit_code == 1
        assert "Invalid status" in result.output
        # unchanged
        assert _state(initialized)["tasks"][0]["status"] == "Todo"

    def test_unknown_id_fails(self, invoke, initialized: Path) -> None:
        result = invoke("status", "zzzz", "done")
        assert result.exit_code == 1
        assert "No task found" in result.output


# --------------------------------------------------------------------------
# remove
# --------------------------------------------------------------------------
class TestRemove:
    def test_remove_persists(self, invoke, initialized: Path) -> None:
        invoke("add", "doomed")
        tid = _first_id(initialized)
        result = invoke("remove", tid)
        assert result.exit_code == 0
        assert _state(initialized)["tasks"] == []

    def test_remove_only_target(self, invoke, initialized: Path) -> None:
        invoke("add", "keep")
        invoke("add", "drop")
        keep_id, drop_id = _ids(initialized)
        invoke("remove", drop_id)
        assert _ids(initialized) == [keep_id]

    def test_unknown_id_fails(self, invoke, initialized: Path) -> None:
        result = invoke("remove", "zzzz")
        assert result.exit_code == 1
        assert "No task found" in result.output


# --------------------------------------------------------------------------
# misc
# --------------------------------------------------------------------------
class TestMisc:
    def test_version(self, invoke) -> None:
        result = invoke("--version")
        assert result.exit_code == 0
        assert "trackr" in result.output

    def test_no_args_shows_help(self, invoke) -> None:
        result = invoke()
        # no_args_is_help -> exits 0 with usage
        assert "Usage" in result.output

    def test_full_lifecycle(self, invoke, workdir: Path) -> None:
        assert invoke("init").exit_code == 0
        assert invoke("add", "step one").exit_code == 0
        tid = _first_id(workdir)
        assert invoke("status", tid, "in progress").exit_code == 0
        assert invoke("status", tid, "done").exit_code == 0
        assert invoke("remove", tid).exit_code == 0
        assert _state(workdir)["tasks"] == []
