"""Shared pytest fixtures.

Every test runs inside a throwaway ``tmp_path`` directory (via
``monkeypatch.chdir``) so the real repository is never touched and each test
gets its own isolated ``.trackr/`` store.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from trackr.cli import app
from trackr.storage import init_store


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Chdir into an isolated temp directory; yield it. No .trackr/ yet."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def initialized(workdir: Path) -> Path:
    """Like ``workdir`` but with the store already initialized."""
    init_store(workdir)
    return workdir


@pytest.fixture
def runner() -> CliRunner:
    """A Typer/Click CLI runner for invoking commands in-process."""
    return CliRunner()


@pytest.fixture
def invoke(runner: CliRunner):
    """Convenience: invoke the trackr app with a list of args -> Result."""

    def _invoke(*args: str):
        return runner.invoke(app, list(args))

    return _invoke
