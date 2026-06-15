"""Persistence layer: locate, create, read and write the ``.tasks`` store.

State lives in ``<repo-root>/.tasks/state.json``. Like Git, commands work
from any subdirectory by walking parent directories until a ``.tasks/`` is
found. Writes are atomic (temp file + ``os.replace``) so the JSON can never
be left half-written if the process dies mid-save.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path

from trackr.errors import CorruptState, NotInitialized
from trackr.models import Task

STORE_DIRNAME = ".tasks"
STATE_FILENAME = "state.json"
STATE_VERSION = 3
_ID_BYTES = 2  # 2 bytes -> 4 hex chars


# --------------------------------------------------------------------------
# Locating the store
# --------------------------------------------------------------------------
def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` (default: cwd) to find a ``.tasks/`` dir.

    Returns the directory that *contains* ``.tasks/``. Raises
    :class:`NotInitialized` if none is found up to the filesystem root.
    """
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / STORE_DIRNAME).is_dir():
            return directory
    raise NotInitialized()


def _store_dir(root: Path) -> Path:
    return root / STORE_DIRNAME


def _state_path(root: Path) -> Path:
    return _store_dir(root) / STATE_FILENAME


# --------------------------------------------------------------------------
# Initialization
# --------------------------------------------------------------------------
def init_store(cwd: Path | None = None) -> tuple[Path, bool]:
    """Create ``.tasks/state.json`` under ``cwd`` (default: current dir).

    Returns ``(store_dir, created)`` where ``created`` is ``False`` if the
    store already existed, letting the CLI print a graceful message instead
    of failing.
    """
    root = (cwd or Path.cwd()).resolve()
    store = _store_dir(root)
    if store.exists():
        return store, False

    store.mkdir(parents=True, exist_ok=False)
    _write_state_file(_state_path(root), [])
    return store, True


# --------------------------------------------------------------------------
# Read / write
# --------------------------------------------------------------------------
def load_tasks(root: Path) -> list[Task]:
    """Load and deserialize all tasks for the repo rooted at ``root``."""
    path = _state_path(root)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return [Task.from_dict(item) for item in data.get("tasks", [])]
    except FileNotFoundError:
        # .tasks/ exists but state.json vanished -> treat as empty store.
        return []
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CorruptState(str(path)) from exc


def save_tasks(root: Path, tasks: list[Task]) -> None:
    """Persist ``tasks`` atomically to the repo's state file."""
    _write_state_file(_state_path(root), tasks)


def _write_state_file(path: Path, tasks: list[Task]) -> None:
    """Atomically write the state JSON (temp file in same dir + os.replace)."""
    payload = {
        "version": STATE_VERSION,
        "tasks": [t.to_dict() for t in tasks],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)  # atomic on POSIX & Windows
    except BaseException:
        # Clean up the temp file on any failure, then re-raise.
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# ID generation
# --------------------------------------------------------------------------
def generate_id(existing: set[str]) -> str:
    """Return a fresh 4-char hex ID not present in ``existing``.

    With 65,536 possible IDs and an expected <1k tasks, collisions are rare;
    we loop just in case. After many attempts we widen the ID to guarantee
    termination even in pathological cases.
    """
    for _ in range(1000):
        candidate = secrets.token_hex(_ID_BYTES)
        if candidate not in existing:
            return candidate
    # Extremely unlikely fallback: widen the space.
    while True:  # pragma: no cover
        candidate = secrets.token_hex(_ID_BYTES + 2)
        if candidate not in existing:
            return candidate


def find_task(tasks: list[Task], task_id: str) -> Task | None:
    """Return the task matching ``task_id`` (case-insensitive), or ``None``."""
    needle = task_id.strip().lower()
    for task in tasks:
        if task.id.lower() == needle:
            return task
    return None
