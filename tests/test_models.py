"""Unit tests for trackr.models: Status coercion and Task serialization."""

from __future__ import annotations

import pytest

from trackr.errors import InvalidStatus
from trackr.models import Status, Task


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
        assert set(d) == {"id", "description", "status", "created_at"}

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
