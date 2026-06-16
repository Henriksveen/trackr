"""Unit tests for trackr.models: Status coercion and Task serialization."""

from __future__ import annotations

import pytest

from trackr.errors import InvalidStatus
from trackr.models import Status, Task, is_blocked, open_blockers, topo_order, would_cycle


class TestStatusCoerce:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Todo", Status.TODO),
            ("todo", Status.TODO),
            ("  TODO  ", Status.TODO),
            ("to do", Status.TODO),
            ("open", Status.TODO),
            ("In Progress", Status.IN_PROGRESS),
            ("in progress", Status.IN_PROGRESS),
            ("INPROGRESS", Status.IN_PROGRESS),
            ("wip", Status.IN_PROGRESS),
            ("ip", Status.IN_PROGRESS),
            ("doing", Status.IN_PROGRESS),
            ("Done", Status.DONE),
            ("done", Status.DONE),
            ("complete", Status.DONE),
            ("finished", Status.DONE),
            # whitespace collapsing: multiple spaces between words
            ("in     progress", Status.IN_PROGRESS),
        ],
    )
    def test_aliases_resolve(self, raw: str, expected: Status) -> None:
        assert Status.coerce(raw) is expected

    @pytest.mark.parametrize("bad", ["banana", "", "   ", "donezo", "to-do"])
    def test_invalid_raises(self, bad: str) -> None:
        with pytest.raises(InvalidStatus):
            Status.coerce(bad)

    def test_invalid_message_lists_valid(self) -> None:
        with pytest.raises(InvalidStatus) as exc:
            Status.coerce("nope")
        msg = str(exc.value)
        assert "Todo" in msg and "In Progress" in msg and "Done" in msg

    def test_str_returns_value(self) -> None:
        assert str(Status.IN_PROGRESS) == "In Progress"


class TestTaskSerde:
    def test_roundtrip(self) -> None:
        original = Task(id="a1b2", description="hello", status=Status.IN_PROGRESS)
        restored = Task.from_dict(original.to_dict())
        assert restored == original

    def test_to_dict_uses_status_value(self) -> None:
        d = Task(id="x", description="d", status=Status.DONE).to_dict()
        assert d["status"] == "Done"
        assert set(d) == {"id", "description", "status", "created_at", "depends_on", "tags"}

    def test_defaults(self) -> None:
        t = Task(id="x", description="d")
        assert t.status is Status.TODO
        assert t.created_at  # auto-populated ISO timestamp

    def test_created_display_formats_date(self) -> None:
        t = Task(id="x", description="d", created_at="2026-06-15T12:19:07+00:00")
        assert t.created_display() == "2026-06-15"

    def test_created_display_fallback_on_garbage(self) -> None:
        t = Task(id="x", description="d", created_at="not-a-date")
        assert t.created_display() == "not-a-date"


class TestTaskDependencies:
    def test_depends_on_defaults_empty(self) -> None:
        t = Task(id="x", description="d")
        assert t.depends_on == []

    def test_to_dict_includes_depends_on(self) -> None:
        t = Task(id="x", description="d", depends_on=["aaaa"])
        d = t.to_dict()
        assert d["depends_on"] == ["aaaa"]
        assert set(d) == {"id", "description", "status", "created_at", "depends_on", "tags"}

    def test_from_dict_roundtrip_with_depends_on(self) -> None:
        original = Task(id="a1b2", description="hello", depends_on=["cccc"])
        restored = Task.from_dict(original.to_dict())
        assert restored == original
        assert restored.depends_on == ["cccc"]

    def test_from_dict_missing_depends_on_defaults_empty(self) -> None:
        """v1 records without depends_on field must load without error."""
        d = {
            "id": "a1b2",
            "description": "old task",
            "status": "Todo",
            "created_at": "2026-06-15T10:00:00+00:00",
        }
        t = Task.from_dict(d)
        assert t.depends_on == []


class TestTaskTags:
    def test_tags_defaults_empty(self) -> None:
        t = Task(id="x", description="d")
        assert t.tags == []

    def test_to_dict_includes_tags(self) -> None:
        t = Task(id="x", description="d", tags=["feature", "urgent"])
        d = t.to_dict()
        assert d["tags"] == ["feature", "urgent"]
        assert set(d) == {"id", "description", "status", "created_at", "depends_on", "tags"}

    def test_from_dict_roundtrip_with_tags(self) -> None:
        original = Task(id="a1b2", description="hello", tags=["bugfix"])
        restored = Task.from_dict(original.to_dict())
        assert restored == original
        assert restored.tags == ["bugfix"]

    def test_from_dict_missing_tags_defaults_empty(self) -> None:
        """v2 records without tags field must load without error (backward compat)."""
        d = {
            "id": "a1b2",
            "description": "old task",
            "status": "Todo",
            "created_at": "2026-06-15T10:00:00+00:00",
            "depends_on": [],
        }
        t = Task.from_dict(d)
        assert t.tags == []


class TestGraphHelpers:
    def _tasks(self) -> tuple[Task, Task, Task]:
        a = Task(id="aaaa", description="A")
        b = Task(id="bbbb", description="B")
        c = Task(id="cccc", description="C")
        return a, b, c

    # is_blocked
    def test_not_blocked_no_deps(self) -> None:
        a, b, c = self._tasks()
        assert is_blocked(a, [a, b, c]) is False

    def test_blocked_when_blocker_not_done(self) -> None:
        a, b, _ = self._tasks()
        a.depends_on = ["bbbb"]
        assert is_blocked(a, [a, b]) is True

    def test_not_blocked_when_all_blockers_done(self) -> None:
        a, b, _ = self._tasks()
        b.status = Status.DONE
        a.depends_on = ["bbbb"]
        assert is_blocked(a, [a, b]) is False

    def test_not_blocked_when_blocker_missing(self) -> None:
        """Dangling ref (blocker deleted) — should not block."""
        a, _, _ = self._tasks()
        a.depends_on = ["ffff"]  # doesn't exist
        assert is_blocked(a, [a]) is False

    # open_blockers
    def test_open_blockers_returns_only_open(self) -> None:
        a, b, c = self._tasks()
        c.status = Status.DONE
        a.depends_on = ["bbbb", "cccc"]
        result = open_blockers(a, [a, b, c])
        assert result == [b]

    def test_open_blockers_empty_when_no_deps(self) -> None:
        a, b, _ = self._tasks()
        assert open_blockers(a, [a, b]) == []

    # would_cycle
    def test_no_cycle_for_fresh_link(self) -> None:
        a, b, _ = self._tasks()
        assert would_cycle([a, b], "aaaa", "bbbb") is False

    def test_direct_cycle(self) -> None:
        a, b, _ = self._tasks()
        b.depends_on = ["aaaa"]  # b already depends on a
        # linking a -> b would create a->b->a
        assert would_cycle([a, b], "aaaa", "bbbb") is True

    def test_transitive_cycle(self) -> None:
        a, b, c = self._tasks()
        b.depends_on = ["cccc"]
        c.depends_on = ["aaaa"]
        # linking a -> b would create a->b->c->a
        assert would_cycle([a, b, c], "aaaa", "bbbb") is True

    def test_dag_no_cycle(self) -> None:
        a, b, c = self._tasks()
        b.depends_on = ["cccc"]  # b -> c (c is independent)
        # linking a -> b: a->b->c — no cycle
        assert would_cycle([a, b, c], "aaaa", "bbbb") is False


class TestTopoOrder:
    """Tests for topo_order: blockers appear before the tasks that depend on them."""

    def _t(self, tid: str, desc: str = "", depends_on: list[str] | None = None) -> Task:
        return Task(id=tid, description=desc or tid, depends_on=depends_on or [])

    def test_empty_returns_empty(self) -> None:
        assert topo_order([]) == []

    def test_single_task_unchanged(self) -> None:
        t = self._t("aaaa")
        assert topo_order([t]) == [t]

    def test_independent_tasks_preserve_insertion_order(self) -> None:
        a = self._t("aaaa")
        b = self._t("bbbb")
        c = self._t("cccc")
        result = topo_order([a, b, c])
        assert result == [a, b, c]

    def test_blocker_before_dependent(self) -> None:
        # B is added first; A depends on B → B must appear before A
        b = self._t("bbbb")
        a = self._t("aaaa", depends_on=["bbbb"])
        # Regardless of insertion order, B should come first
        assert topo_order([a, b]) == [b, a]
        assert topo_order([b, a]) == [b, a]

    def test_chain(self) -> None:
        # A depends on B, B depends on C → order: C, B, A
        c = self._t("cccc")
        b = self._t("bbbb", depends_on=["cccc"])
        a = self._t("aaaa", depends_on=["bbbb"])
        result = topo_order([a, b, c])
        assert result.index(c) < result.index(b) < result.index(a)

    def test_diamond(self) -> None:
        # D is root; B depends on D; C depends on D; A depends on B and C
        d = self._t("dddd")
        b = self._t("bbbb", depends_on=["dddd"])
        c = self._t("cccc", depends_on=["dddd"])
        a = self._t("aaaa", depends_on=["bbbb", "cccc"])
        result = topo_order([a, b, c, d])
        # D first, A last; B and C are between
        ids = [t.id for t in result]
        assert ids[0] == "dddd"
        assert ids[-1] == "aaaa"
        assert set(ids[1:3]) == {"bbbb", "cccc"}

    def test_stability_among_independent(self) -> None:
        # x and y have no relationship — original order must be preserved
        x = self._t("xxxx")
        y = self._t("yyyy")
        # x before y in input → x before y in output
        assert topo_order([x, y]) == [x, y]
        assert topo_order([y, x]) == [y, x]

    def test_dep_pointing_to_absent_id_ignored(self) -> None:
        # "ffff" is not in the list — should be treated as no edge
        a = self._t("aaaa", depends_on=["ffff"])
        b = self._t("bbbb")
        result = topo_order([a, b])
        assert {t.id for t in result} == {"aaaa", "bbbb"}  # both present, no crash

    def test_cycle_safe_returns_all_tasks(self) -> None:
        # Hand-built cycle (bypasses would_cycle guard) — all tasks must be returned
        a = self._t("aaaa", depends_on=["bbbb"])
        b = self._t("bbbb", depends_on=["aaaa"])
        result = topo_order([a, b])
        assert {t.id for t in result} == {"aaaa", "bbbb"}  # no infinite loop, no dropped nodes

    def test_mixed_linked_and_independent(self) -> None:
        # z is independent; a depends on b → b, a in order; z floats by insertion
        z = self._t("zzzz")
        b = self._t("bbbb")
        a = self._t("aaaa", depends_on=["bbbb"])
        result = topo_order([z, a, b])
        # b must appear before a; z has no constraint
        assert result.index(b) < result.index(a)
