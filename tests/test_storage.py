"""Unit tests for trackr.storage: discovery, persistence, ID generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trackr.errors import CorruptState, NotInitialized
from trackr.models import Status, Task
from trackr.storage import (
    STATE_FILENAME,
    STORE_DIRNAME,
    find_repo_root,
    find_task,
    generate_id,
    init_store,
    load_tasks,
    save_tasks,
)


class TestInit:
    def test_creates_store_and_state(self, workdir: Path) -> None:
        store, created = init_store(workdir)
        assert created is True
        assert store == workdir / STORE_DIRNAME
        assert (store / STATE_FILENAME).is_file()
        # fresh state is a valid, empty payload
        payload = json.loads((store / STATE_FILENAME).read_text())
        assert payload == {"version": 1, "tasks": []}

    def test_idempotent_returns_false(self, workdir: Path) -> None:
        init_store(workdir)
        _, created_again = init_store(workdir)
        assert created_again is False


class TestFindRepoRoot:
    def test_found_in_cwd(self, initialized: Path) -> None:
        assert find_repo_root(initialized) == initialized

    def test_walks_up_from_subdir(self, initialized: Path) -> None:
        nested = initialized / "a" / "b" / "c"
        nested.mkdir(parents=True)
        assert find_repo_root(nested) == initialized

    def test_raises_when_absent(self, workdir: Path) -> None:
        with pytest.raises(NotInitialized):
            find_repo_root(workdir)


class TestLoadSave:
    def test_empty_after_init(self, initialized: Path) -> None:
        assert load_tasks(initialized) == []

    def test_save_then_load_roundtrip(self, initialized: Path) -> None:
        tasks = [
            Task(id="aaaa", description="one"),
            Task(id="bbbb", description="two", status=Status.DONE),
        ]
        save_tasks(initialized, tasks)
        loaded = load_tasks(initialized)
        assert loaded == tasks

    def test_save_is_atomic_no_tmp_left(self, initialized: Path) -> None:
        save_tasks(initialized, [Task(id="aaaa", description="one")])
        leftovers = list((initialized / STORE_DIRNAME).glob("*.tmp"))
        assert leftovers == []

    def test_missing_state_file_treated_as_empty(self, initialized: Path) -> None:
        # .tasks/ exists but state.json removed
        (initialized / STORE_DIRNAME / STATE_FILENAME).unlink()
        assert load_tasks(initialized) == []

    def test_corrupt_state_raises(self, initialized: Path) -> None:
        (initialized / STORE_DIRNAME / STATE_FILENAME).write_text("{not json")
        with pytest.raises(CorruptState):
            load_tasks(initialized)


class TestGenerateId:
    def test_format_is_4_hex(self) -> None:
        new = generate_id(set())
        assert len(new) == 4
        int(new, 16)  # parses as hex (raises ValueError otherwise)

    def test_avoids_existing(self) -> None:
        # Generated id must never collide with the supplied set.
        existing = {generate_id(set()) for _ in range(50)}
        for _ in range(200):
            new = generate_id(existing)
            assert new not in existing

    def test_widens_when_4hex_exhausted(self) -> None:
        # When the entire 4-hex space is taken, the generator must still
        # terminate by widening to a longer id (never loop forever / collide).
        full = {f"{i:04x}" for i in range(0x10000)}
        new = generate_id(full)
        assert new not in full
        assert len(new) > 4


class TestFindTask:
    def test_case_insensitive_match(self) -> None:
        tasks = [Task(id="a1b2", description="d")]
        assert find_task(tasks, "A1B2") is tasks[0]

    def test_returns_none_when_absent(self) -> None:
        assert find_task([Task(id="a1b2", description="d")], "ffff") is None
