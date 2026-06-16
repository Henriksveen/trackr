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


# --------------------------------------------------------------------------
# tags
# --------------------------------------------------------------------------
class TestTagAdd:
    def test_add_with_tags_persists(self, invoke, initialized: Path) -> None:
        result = invoke("add", "My task", "--tags", "feature,urgent")
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        assert tasks[0]["tags"] == ["feature", "urgent"]

    def test_add_without_tags_defaults_empty(self, invoke, initialized: Path) -> None:
        invoke("add", "My task")
        tasks = _state(initialized)["tasks"]
        assert tasks[0]["tags"] == []

    def test_add_tags_shown_in_output(self, invoke, initialized: Path) -> None:
        result = invoke("add", "My task", "--tags", "feature")
        assert "feature" in result.output

    def test_add_tags_whitespace_stripped(self, invoke, initialized: Path) -> None:
        invoke("add", "My task", "--tags", " feature , urgent ")
        tasks = _state(initialized)["tasks"]
        assert tasks[0]["tags"] == ["feature", "urgent"]

    def test_add_empty_tag_rejected(self, invoke, initialized: Path) -> None:
        result = invoke("add", "My task", "--tags", ",")
        assert result.exit_code == 1
        assert "tag" in result.output.lower()


class TestTagCommand:
    def test_tag_adds_tag(self, invoke, initialized: Path) -> None:
        invoke("add", "My task")
        tid = _first_id(initialized)
        result = invoke("tag", tid, "feature")
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        assert "feature" in tasks[0]["tags"]

    def test_tag_multiple_tags(self, invoke, initialized: Path) -> None:
        invoke("add", "My task")
        tid = _first_id(initialized)
        invoke("tag", tid, "feature")
        invoke("tag", tid, "urgent")
        tasks = _state(initialized)["tasks"]
        assert set(tasks[0]["tags"]) == {"feature", "urgent"}

    def test_tag_idempotent(self, invoke, initialized: Path) -> None:
        invoke("add", "My task")
        tid = _first_id(initialized)
        invoke("tag", tid, "feature")
        result = invoke("tag", tid, "feature")
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        assert tasks[0]["tags"].count("feature") == 1

    def test_tag_unknown_id_fails(self, invoke, initialized: Path) -> None:
        result = invoke("tag", "zzzz", "feature")
        assert result.exit_code == 1
        assert "No task found" in result.output

    def test_tag_empty_label_rejected(self, invoke, initialized: Path) -> None:
        invoke("add", "My task")
        tid = _first_id(initialized)
        result = invoke("tag", tid, "  ")
        assert result.exit_code == 1
        assert "tag" in result.output.lower()


class TestUntagCommand:
    def test_untag_removes_tag(self, invoke, initialized: Path) -> None:
        invoke("add", "My task", "--tags", "feature,urgent")
        tid = _first_id(initialized)
        result = invoke("untag", tid, "feature")
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        assert "feature" not in tasks[0]["tags"]
        assert "urgent" in tasks[0]["tags"]

    def test_untag_not_present_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "My task")
        tid = _first_id(initialized)
        result = invoke("untag", tid, "nosuch")
        assert result.exit_code == 1
        assert "not tagged" in result.output.lower() or "nosuch" in result.output.lower()

    def test_untag_unknown_id_fails(self, invoke, initialized: Path) -> None:
        result = invoke("untag", "zzzz", "feature")
        assert result.exit_code == 1
        assert "No task found" in result.output


class TestListTagFilter:
    def test_list_tag_filter_shows_matching(self, invoke, initialized: Path) -> None:
        invoke("add", "Feature task", "--tags", "feature")
        invoke("add", "Bug task", "--tags", "bug")
        result = invoke("list", "--tag", "feature")
        assert result.exit_code == 0
        assert "Feature task" in result.output
        assert "Bug task" not in result.output

    def test_list_tag_filter_no_match_empty(self, invoke, initialized: Path) -> None:
        invoke("add", "Feature task", "--tags", "feature")
        result = invoke("list", "--tag", "bug")
        assert result.exit_code == 0
        assert "Feature task" not in result.output

    def test_list_tag_filter_multiple_tags_any_match(
        self, invoke, initialized: Path
    ) -> None:
        invoke("add", "Task A", "--tags", "alpha")
        invoke("add", "Task B", "--tags", "beta")
        invoke("add", "Task C", "--tags", "gamma")
        result = invoke("list", "--tag", "alpha", "--tag", "beta")
        assert "Task A" in result.output
        assert "Task B" in result.output
        assert "Task C" not in result.output


class TestShowTags:
    def test_show_displays_tags(self, invoke, initialized: Path) -> None:
        invoke("add", "My task", "--tags", "feature,urgent")
        tid = _first_id(initialized)
        result = invoke("show", tid)
        assert result.exit_code == 0
        assert "feature" in result.output
        assert "urgent" in result.output

    def test_show_no_tags_shows_none(self, invoke, initialized: Path) -> None:
        invoke("add", "My task")
        tid = _first_id(initialized)
        result = invoke("show", tid)
        assert result.exit_code == 0
        # should show something indicating no tags
        assert "none" in result.output.lower() or "tags" in result.output.lower()


class TestListShowsTags:
    def test_list_shows_tags_column(self, invoke, initialized: Path) -> None:
        invoke("add", "My task", "--tags", "feature")
        result = invoke("list")
        assert "feature" in result.output

class TestLink:
    def test_link_persists_depends_on(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        result = invoke("link", a_id, b_id)
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        a_task = next(t for t in tasks if t["id"] == a_id)
        assert b_id in a_task["depends_on"]

    def test_link_idempotent_noop(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)
        result = invoke("link", a_id, b_id)
        assert result.exit_code == 0
        # still only one entry
        tasks = _state(initialized)["tasks"]
        a_task = next(t for t in tasks if t["id"] == a_id)
        assert a_task["depends_on"].count(b_id) == 1

    def test_link_self_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        tid = _first_id(initialized)
        result = invoke("link", tid, tid)
        assert result.exit_code == 1
        assert "itself" in result.output.lower() or "self" in result.output.lower()

    def test_link_cycle_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)   # a depends on b
        result = invoke("link", b_id, a_id)  # b depends on a — cycle
        assert result.exit_code == 1
        assert "cycle" in result.output.lower() or "circular" in result.output.lower()

    def test_link_unknown_dependent_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        tid = _first_id(initialized)
        result = invoke("link", "zzzz", tid)
        assert result.exit_code == 1
        assert "No task found" in result.output

    def test_link_unknown_blocker_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        tid = _first_id(initialized)
        result = invoke("link", tid, "zzzz")
        assert result.exit_code == 1
        assert "No task found" in result.output

    def test_link_case_insensitive_ids(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        result = invoke("link", a_id.upper(), b_id.upper())
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        a_task = next(t for t in tasks if t["id"] == a_id)
        assert b_id in a_task["depends_on"]


# --------------------------------------------------------------------------
# unlink
# --------------------------------------------------------------------------
class TestUnlink:
    def test_unlink_removes_dep(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)
        result = invoke("unlink", a_id, b_id)
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        a_task = next(t for t in tasks if t["id"] == a_id)
        assert a_task["depends_on"] == []

    def test_unlink_not_linked_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        result = invoke("unlink", a_id, b_id)
        assert result.exit_code == 1
        assert "not linked" in result.output.lower() or "not depend" in result.output.lower()

    def test_unlink_unknown_id_fails(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        tid = _first_id(initialized)
        result = invoke("unlink", "zzzz", tid)
        assert result.exit_code == 1
        assert "No task found" in result.output


# --------------------------------------------------------------------------
# show
# --------------------------------------------------------------------------
class TestShow:
    def test_show_displays_task_info(self, invoke, initialized: Path) -> None:
        invoke("add", "my important task")
        tid = _first_id(initialized)
        result = invoke("show", tid)
        assert result.exit_code == 0
        assert "my important task" in result.output
        assert tid in result.output

    def test_show_displays_blockers(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)
        result = invoke("show", a_id)
        assert result.exit_code == 0
        assert b_id in result.output

    def test_show_displays_blocks(self, invoke, initialized: Path) -> None:
        """show should display what this task blocks (reverse direction)."""
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)  # a depends on b
        result = invoke("show", b_id)   # b blocks a
        assert result.exit_code == 0
        assert a_id in result.output

    def test_show_unknown_id_fails(self, invoke, initialized: Path) -> None:
        result = invoke("show", "zzzz")
        assert result.exit_code == 1
        assert "No task found" in result.output


# --------------------------------------------------------------------------
# list with deps column
# --------------------------------------------------------------------------
class TestListDeps:
    def test_blocked_task_shown_in_list(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)
        result = invoke("list")
        assert result.exit_code == 0
        # Both tasks shown (neither is Done); blocked marker must appear
        assert "blocked" in result.output.lower() or "⊘" in result.output

    def test_no_dep_marker_when_unblocked(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)
        # Mark blocker done — A is no longer blocked
        invoke("status", b_id, "done")
        result = invoke("list", "--all")
        assert result.exit_code == 0
        # The "blocked" marker should NOT appear for A
        lines = [l for l in result.output.splitlines() if a_id in l]
        assert lines  # A is listed
        assert not any("blocked" in l.lower() or "⊘" in l for l in lines)


# --------------------------------------------------------------------------
# status warns when blocked
# --------------------------------------------------------------------------
class TestStatusWithDeps:
    def test_status_done_with_open_blocker_warns_but_succeeds(
        self, invoke, initialized: Path
    ) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)  # a depends on b (b is still Todo)
        result = invoke("status", a_id, "done")
        # Must succeed (exit 0) — warn only
        assert result.exit_code == 0
        assert _state(initialized)["tasks"][0]["status"] == "Done" or \
               next(t for t in _state(initialized)["tasks"] if t["id"] == a_id)["status"] == "Done"
        # Must print a warning
        assert "warn" in result.output.lower() or "blocked" in result.output.lower() \
               or "open" in result.output.lower() or b_id in result.output


# --------------------------------------------------------------------------
# remove auto-cleans deps
# --------------------------------------------------------------------------
class TestRemoveWithDeps:
    def test_remove_blocker_cleans_dependent_ref(self, invoke, initialized: Path) -> None:
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        invoke("link", a_id, b_id)  # a depends on b
        result = invoke("remove", b_id)  # remove blocker b
        assert result.exit_code == 0
        tasks = _state(initialized)["tasks"]
        a_task = next(t for t in tasks if t["id"] == a_id)
        assert a_task["depends_on"] == []
        # Should warn
        assert a_id in result.output or "depend" in result.output.lower() or "clean" in result.output.lower()


# --------------------------------------------------------------------------
# list: topological ordering
# --------------------------------------------------------------------------
class TestListTopoOrder:
    def test_blocker_appears_before_dependent_in_output(
        self, invoke, initialized: Path
    ) -> None:
        # Add dependent first, then blocker — after linking, blocker must render first
        invoke("add", "Dependent")
        invoke("add", "Blocker")
        dep_id, blk_id = _ids(initialized)
        invoke("link", dep_id, blk_id)  # dep depends on blk → blk must come first

        result = invoke("list")
        assert result.exit_code == 0
        out = result.output
        # Both IDs appear; blocker's row comes before dependent's row
        assert blk_id in out and dep_id in out
        assert out.index(blk_id) < out.index(dep_id)

    def test_stored_order_unchanged_after_link(
        self, invoke, initialized: Path
    ) -> None:
        # Linking must NOT reorder the persisted tasks array
        invoke("add", "A")
        invoke("add", "B")
        a_id, b_id = _ids(initialized)
        original_order = _ids(initialized)
        invoke("link", a_id, b_id)  # a depends on b
        assert _ids(initialized) == original_order  # storage untouched

    def test_chain_ordering_in_output(self, invoke, initialized: Path) -> None:
        # Three tasks: C → B → A (A depends on B, B depends on C)
        # Added in order: A, B, C
        invoke("add", "Task A")
        invoke("add", "Task B")
        invoke("add", "Task C")
        a_id, b_id, c_id = _ids(initialized)
        invoke("link", a_id, b_id)  # a depends on b
        invoke("link", b_id, c_id)  # b depends on c

        result = invoke("list")
        assert result.exit_code == 0
        out = result.output
        # Pipeline order: C before B before A
        assert out.index(c_id) < out.index(b_id) < out.index(a_id)

    def test_independent_tasks_preserve_insertion_order(
        self, invoke, initialized: Path
    ) -> None:
        # No links — output order should match addition order
        invoke("add", "First")
        invoke("add", "Second")
        invoke("add", "Third")
        first_id, second_id, third_id = _ids(initialized)

        result = invoke("list")
        assert result.exit_code == 0
        out = result.output
        assert out.index(first_id) < out.index(second_id) < out.index(third_id)

    def test_done_blocker_hidden_no_crash(self, invoke, initialized: Path) -> None:
        # Blocker is Done (hidden by default), dependent is Todo — no crash, dependent shown
        invoke("add", "Blocker")
        invoke("add", "Dependent")
        blk_id, dep_id = _ids(initialized)
        invoke("link", dep_id, blk_id)
        invoke("status", blk_id, "done")

        result = invoke("list")
        assert result.exit_code == 0
        assert dep_id in result.output
        # Blocker is Done, hidden by default
        assert blk_id not in result.output
