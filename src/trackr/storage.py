"""Persistence layer: locate, create, read and write the ``.trackr`` store.

State lives in ``<repo-root>/.trackr/<project>.json``. Like Git, commands
work from any subdirectory by walking parent directories until a ``.trackr/``
directory is found. The active project is recorded in ``.trackr/active`` as
a plain-text single line. Writes are atomic (temp file + ``os.replace``) so
JSON can never be left half-written if the process dies mid-save.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import tempfile
from pathlib import Path

from trackr.errors import (
    CorruptState,
    InvalidProjectName,
    NotInitialized,
    ProjectExists,
    ProjectNotFound,
)
from trackr.models import Task

STORE_DIRNAME = ".trackr"
ACTIVE_FILENAME = "active"
DEFAULT_PROJECT = "default"
PROJECT_SUFFIX = ".json"
STATE_VERSION = 3
_ID_BYTES = 2  # 2 bytes -> 4 hex chars

# Reserved name: the pointer file itself has no suffix so "active" can't
# collide, but we reserve it anyway to avoid user confusion.
_RESERVED_NAMES = frozenset({"active"})
_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


# --------------------------------------------------------------------------
# Locating the store
# --------------------------------------------------------------------------
def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from ``start`` (default: cwd) to find a ``.trackr/`` dir.

    Returns the directory that *contains* ``.trackr/``. Raises
    :class:`NotInitialized` if none is found up to the filesystem root.
    """
    current = (start or Path.cwd()).resolve()
    for directory in (current, *current.parents):
        if (directory / STORE_DIRNAME).is_dir():
            return directory
    raise NotInitialized()


def _store_dir(root: Path) -> Path:
    return root / STORE_DIRNAME


def _project_path(root: Path, name: str) -> Path:
    return _store_dir(root) / f"{name}{PROJECT_SUFFIX}"


def _active_path(root: Path) -> Path:
    return _store_dir(root) / ACTIVE_FILENAME


# --------------------------------------------------------------------------
# Atomic helpers
# --------------------------------------------------------------------------
def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write *text* to *path* (temp file + fsync + os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _write_state_file(path: Path, tasks: list[Task]) -> None:
    """Atomically write the state JSON."""
    payload = {
        "version": STATE_VERSION,
        "tasks": [t.to_dict() for t in tasks],
    }
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------
# Active project pointer
# --------------------------------------------------------------------------
def read_active(root: Path) -> str:
    """Return the active project name, defaulting to ``DEFAULT_PROJECT``."""
    path = _active_path(root)
    try:
        return path.read_text(encoding="utf-8").strip() or DEFAULT_PROJECT
    except FileNotFoundError:
        return DEFAULT_PROJECT


def set_active(root: Path, name: str) -> None:
    """Set the active project pointer. Raises :class:`ProjectNotFound` if missing."""
    if not project_exists(root, name):
        raise ProjectNotFound(name)
    _atomic_write_text(_active_path(root), name + "\n")


# --------------------------------------------------------------------------
# Project management
# --------------------------------------------------------------------------
def _validate_project_name(name: str) -> None:
    """Raise :class:`InvalidProjectName` if *name* is not acceptable."""
    if not name:
        raise InvalidProjectName(name, "name must not be empty")
    if name in _RESERVED_NAMES:
        raise InvalidProjectName(name, f"'{name}' is a reserved name")
    if name in (".", ".."):
        raise InvalidProjectName(name, "name must not be '.' or '..'")
    if "/" in name or "\\" in name:
        raise InvalidProjectName(name, "name must not contain path separators")
    if not _NAME_RE.match(name):
        raise InvalidProjectName(name, "name contains invalid characters")


def project_exists(root: Path, name: str) -> bool:
    """Return True if a project state file exists for *name*."""
    return _project_path(root, name).is_file()


def list_projects(root: Path) -> list[str]:
    """Return sorted list of all project names in the store."""
    store = _store_dir(root)
    names = [
        p.stem
        for p in store.glob(f"*{PROJECT_SUFFIX}")
        if p.stem != ACTIVE_FILENAME  # safety: exclude any accidental 'active.json'
    ]
    return sorted(names)


def create_project(root: Path, name: str) -> None:
    """Create a new project state file. Does not switch the active pointer.

    Raises :class:`InvalidProjectName` for bad names,
    :class:`ProjectExists` if already present.
    """
    _validate_project_name(name)
    if project_exists(root, name):
        raise ProjectExists(name)
    _write_state_file(_project_path(root, name), [])


# --------------------------------------------------------------------------
# Initialization
# --------------------------------------------------------------------------
def init_store(cwd: Path | None = None) -> tuple[Path, bool]:
    """Create ``.trackr/`` with ``default.json`` and ``active`` pointer.

    Returns ``(store_dir, created)`` where ``created`` is ``False`` if the
    store already existed, letting the CLI print a graceful message.
    """
    root = (cwd or Path.cwd()).resolve()
    store = _store_dir(root)
    if store.exists():
        return store, False

    store.mkdir(parents=True, exist_ok=False)
    _write_state_file(_project_path(root, DEFAULT_PROJECT), [])
    _atomic_write_text(_active_path(root), DEFAULT_PROJECT + "\n")
    return store, True


# --------------------------------------------------------------------------
# Read / write tasks
# --------------------------------------------------------------------------
def load_tasks(root: Path, project: str | None = None) -> list[Task]:
    """Load and deserialize all tasks for *project* (default: active project)."""
    name = project if project is not None else read_active(root)
    path = _project_path(root, name)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return [Task.from_dict(item) for item in data.get("tasks", [])]
    except FileNotFoundError:
        # Project file missing -> treat as empty store.
        return []
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise CorruptState(str(path)) from exc


def save_tasks(root: Path, tasks: list[Task], project: str | None = None) -> None:
    """Persist ``tasks`` atomically to the project's state file."""
    name = project if project is not None else read_active(root)
    _write_state_file(_project_path(root, name), tasks)


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
