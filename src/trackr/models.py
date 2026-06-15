"""Domain models: task status and the Task record itself."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from trackr.errors import InvalidStatus


class Status(str, Enum):
    """Lifecycle states for a task.

    Inherits from ``str`` (instead of 3.11's ``StrEnum``) so the project
    stays compatible with Python 3.10. ``str`` mix-in means ``Status.TODO``
    serializes directly to its value in JSON.
    """

    TODO = "Todo"
    IN_PROGRESS = "In Progress"
    DONE = "Done"

    def __str__(self) -> str:  # nicer display / f-strings
        return self.value

    @classmethod
    def coerce(cls, raw: str) -> "Status":
        """Map free-form user input to a canonical :class:`Status`.

        Case-insensitive and alias-aware so ``"wip"``, ``"in progress"`` and
        ``"In Progress"`` all resolve to :attr:`IN_PROGRESS`.
        """
        key = " ".join(raw.strip().lower().split())  # collapse whitespace
        if key in _ALIASES:
            return _ALIASES[key]
        raise InvalidStatus(raw, [s.value for s in cls])


# Alias table -> canonical status. Keys are normalized (lowercase, single-spaced).
_ALIASES: dict[str, Status] = {
    # Todo
    "todo": Status.TODO,
    "to do": Status.TODO,
    "td": Status.TODO,
    "open": Status.TODO,
    "new": Status.TODO,
    # In Progress
    "in progress": Status.IN_PROGRESS,
    "inprogress": Status.IN_PROGRESS,
    "progress": Status.IN_PROGRESS,
    "wip": Status.IN_PROGRESS,
    "ip": Status.IN_PROGRESS,
    "doing": Status.IN_PROGRESS,
    "started": Status.IN_PROGRESS,
    # Done
    "done": Status.DONE,
    "complete": Status.DONE,
    "completed": Status.DONE,
    "finished": Status.DONE,
    "closed": Status.DONE,
}


def _utcnow_iso() -> str:
    """Current UTC time as a second-precision ISO-8601 string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Task:
    """A single tracked task."""

    id: str
    description: str
    status: Status = Status.TODO
    created_at: str = field(default_factory=_utcnow_iso)
    depends_on: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # --- serialization -----------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at,
            "depends_on": list(self.depends_on),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            description=data["description"],
            status=Status(data["status"]),
            created_at=data["created_at"],
            depends_on=list(data.get("depends_on", [])),
            tags=list(data.get("tags", [])),
        )

    # --- display helpers ---------------------------------------------------
    def created_display(self) -> str:
        """Human-friendly ``YYYY-MM-DD`` date for table rendering.

        Falls back to the raw stored value if it cannot be parsed.
        """
        try:
            return datetime.fromisoformat(self.created_at).strftime("%Y-%m-%d")
        except ValueError:
            return self.created_at


# --------------------------------------------------------------------------
# Graph helpers — pure domain, no I/O
# --------------------------------------------------------------------------

def _task_index(tasks: list[Task]) -> dict[str, Task]:
    """Build a lowercase-id -> Task lookup dict."""
    return {t.id.lower(): t for t in tasks}


def is_blocked(task: Task, tasks: list[Task]) -> bool:
    """Return True if *task* has at least one blocker that is not Done."""
    index = _task_index(tasks)
    for blocker_id in task.depends_on:
        blocker = index.get(blocker_id.lower())
        if blocker is not None and blocker.status is not Status.DONE:
            return True
    return False


def open_blockers(task: Task, tasks: list[Task]) -> list[Task]:
    """Return the list of blocker tasks that are not yet Done."""
    index = _task_index(tasks)
    result = []
    for blocker_id in task.depends_on:
        blocker = index.get(blocker_id.lower())
        if blocker is not None and blocker.status is not Status.DONE:
            result.append(blocker)
    return result


def would_cycle(tasks: list[Task], dependent_id: str, blocker_id: str) -> bool:
    """Return True if adding ``dependent -> blocker`` would create a cycle.

    Uses DFS: if *dependent_id* is reachable from *blocker_id* through
    existing ``depends_on`` edges, the new link would close a cycle.
    """
    index = _task_index(tasks)
    needle = dependent_id.lower()

    visited: set[str] = set()
    stack = [blocker_id.lower()]
    while stack:
        current = stack.pop()
        if current == needle:
            return True
        if current in visited:
            continue
        visited.add(current)
        node = index.get(current)
        if node is not None:
            for dep in node.depends_on:
                stack.append(dep.lower())
    return False
