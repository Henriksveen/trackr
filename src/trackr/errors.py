"""Custom exceptions for trackr.

A single base class (:class:`TrackrError`) lets the CLI layer catch every
expected, user-facing failure in one place and render a clean one-line
message instead of a Python traceback.
"""

from __future__ import annotations


class TrackrError(Exception):
    """Base class for all expected, user-facing trackr errors."""


class NotInitialized(TrackrError):
    """Raised when a command runs outside an initialized trackr repository."""

    def __init__(self) -> None:
        super().__init__(
            "Not a trackr repository (no .tasks/ directory found).\n"
            "Run 'trackr init' first."
        )


class AlreadyInitialized(TrackrError):
    """Raised internally when init finds an existing store (handled gracefully)."""


class TaskNotFound(TrackrError):
    """Raised when a task ID does not exist in the current state."""

    def __init__(self, task_id: str) -> None:
        self.task_id = task_id
        super().__init__(f"No task found with ID '{task_id}'.")


class InvalidStatus(TrackrError):
    """Raised when a status string cannot be mapped to a known status."""

    def __init__(self, value: str, valid: list[str]) -> None:
        self.value = value
        super().__init__(
            f"Invalid status '{value}'. Valid statuses: {', '.join(valid)}."
        )


class EmptyDescription(TrackrError):
    """Raised when attempting to add a task with a blank description."""

    def __init__(self) -> None:
        super().__init__("Task description must not be empty.")


class CorruptState(TrackrError):
    """Raised when the state file exists but cannot be parsed."""

    def __init__(self, path: str) -> None:
        super().__init__(
            f"State file at '{path}' is corrupt or unreadable. "
            "Fix or delete the .tasks/ directory and re-run 'trackr init'."
        )
