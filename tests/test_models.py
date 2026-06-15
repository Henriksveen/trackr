"""Unit tests for trackr.models: Status coercion and Task serialization."""

from __future__ import annotations

import pytest

from trackr.errors import InvalidStatus
from trackr.models import Status, Task, is_blocked, open_blockers, would_cycle


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
        assert set(d) == {"id", "description", "status", "created_at", "depends_on"}

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
        assert set(d) == {"id", "description", "status", "created_at", "depends_on"}

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
