"""Unit tests for trackr.storage: discovery, persistence, ID generation, projects."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trackr.errors import (
    CorruptState,
    InvalidProjectName,
    NotInitialized,
    ProjectExists,
    ProjectNotFound,
)
from trackr.models import Status, Task
from trackr.storage import (
    ACTIVE_FILENAME,
    DEFAULT_PROJECT,
    STORE_DIRNAME,
    create_project,
    find_repo_root,
    find_task,
    generate_id,
    init_store,
    list_projects,
    load_tasks,
    project_exists,
    read_active,
    save_tasks,
    set_active,
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _state_path(root: Path, project: str = DEFAULT_PROJECT) -> Path:
    return root / STORE_DIRNAME / f"{project}.json"


def _active_path(root: Path) -> Path:
    return root / STORE_DIRNAME / ACTIVE_FILENAME


# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------
class TestConstants:
    def test_store_dirname(self) -> None:
        assert STORE_DIRNAME == ".trackr"

    def test_active_filename(self) -> None:
        assert ACTIVE_FILENAME == "active"

    def test_default_project(self) -> None:
        assert DEFAULT_PROJECT == "default"


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------
class TestInit:
    def test_creates_store_dir(self, workdir: Path) -> None:
        store, created = init_store(workdir)
        assert created is True
        assert store == workdir / STORE_DIRNAME
        assert store.is_dir()

    def test_creates_default_state_file(self, workdir: Path) -> None:
        init_store(workdir)
        path = _state_path(workdir)
        assert path.is_file()
        payload = json.loads(path.read_text())
        assert payload == {"version": 3, "tasks": []}

    def test_creates_active_pointer(self, workdir: Path) -> None:
        init_store(workdir)
        active_path = _active_path(workdir)
        assert active_path.is_file()
        assert active_path.read_text().strip() == DEFAULT_PROJECT

    def test_idempotent_returns_false(self, workdir: Path) -> None:
        init_store(workdir)
        _, created_again = init_store(workdir)
        assert created_again is False


# --------------------------------------------------------------------------
# find_repo_root
# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
# active pointer
# --------------------------------------------------------------------------
class TestActivePointer:
    def test_read_active_returns_default_project(self, initialized: Path) -> None:
        assert read_active(initialized) == DEFAULT_PROJECT

    def test_read_active_missing_file_returns_default(self, initialized: Path) -> None:
        _active_path(initialized).unlink()
        assert read_active(initialized) == DEFAULT_PROJECT

    def test_set_active_changes_pointer(self, initialized: Path) -> None:
        create_project(initialized, "other")
        set_active(initialized, "other")
        assert read_active(initialized) == "other"
        assert _active_path(initialized).read_text().strip() == "other"

    def test_set_active_unknown_project_raises(self, initialized: Path) -> None:
        with pytest.raises(ProjectNotFound):
            set_active(initialized, "ghost")


# --------------------------------------------------------------------------
# list_projects
# --------------------------------------------------------------------------
class TestListProjects:
    def test_initial_has_default(self, initialized: Path) -> None:
        assert list_projects(initialized) == [DEFAULT_PROJECT]

    def test_returns_sorted_names(self, initialized: Path) -> None:
        create_project(initialized, "zebra")
        create_project(initialized, "alpha")
        names = list_projects(initialized)
        assert names == sorted(names)
        assert DEFAULT_PROJECT in names
        assert "zebra" in names
        assert "alpha" in names

    def test_active_file_not_included(self, initialized: Path) -> None:
        """'active' pointer file must not appear in project listing."""
        names = list_projects(initialized)
        assert ACTIVE_FILENAME not in names


# --------------------------------------------------------------------------
# project_exists / create_project
# --------------------------------------------------------------------------
class TestCreateProject:
    def test_project_exists_after_create(self, initialized: Path) -> None:
        create_project(initialized, "sprint1")
        assert project_exists(initialized, "sprint1")

    def test_create_writes_empty_state(self, initialized: Path) -> None:
        create_project(initialized, "sprint1")
        path = _state_path(initialized, "sprint1")
        assert path.is_file()
        payload = json.loads(path.read_text())
        assert payload == {"version": 3, "tasks": []}

    def test_create_does_not_switch_active(self, initialized: Path) -> None:
        create_project(initialized, "sprint1")
        assert read_active(initialized) == DEFAULT_PROJECT

    def test_create_duplicate_raises(self, initialized: Path) -> None:
        create_project(initialized, "sprint1")
        with pytest.raises(ProjectExists):
            create_project(initialized, "sprint1")

    def test_default_project_already_exists(self, initialized: Path) -> None:
        with pytest.raises(ProjectExists):
            create_project(initialized, DEFAULT_PROJECT)


# --------------------------------------------------------------------------
# project name validation
# --------------------------------------------------------------------------
class TestProjectNameValidation:
    @pytest.mark.parametrize("name", [
        "",           # empty
        "a/b",        # path separator
        "a\\b",       # windows separator
        "..",         # parent dir
        ".",          # current dir
        "active",     # reserved pointer file name
        "a b",        # space
        "a\tb",       # tab
    ])
    def test_invalid_names_rejected(self, initialized: Path, name: str) -> None:
        with pytest.raises(InvalidProjectName):
            create_project(initialized, name)

    @pytest.mark.parametrize("name", [
        "sprint1",
        "my-project",
        "v2.0",
        "UPPER",
        "mix_123",
    ])
    def test_valid_names_accepted(self, initialized: Path, name: str) -> None:
        create_project(initialized, name)
        assert project_exists(initialized, name)


# --------------------------------------------------------------------------
# load / save — active-project defaulting
# --------------------------------------------------------------------------
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
        _state_path(initialized).unlink()
        assert load_tasks(initialized) == []

    def test_corrupt_state_raises(self, initialized: Path) -> None:
        _state_path(initialized).write_text("{not json")
        with pytest.raises(CorruptState):
            load_tasks(initialized)

    def test_explicit_project_arg(self, initialized: Path) -> None:
        create_project(initialized, "other")
        tasks = [Task(id="cccc", description="other-task")]
        save_tasks(initialized, tasks, project="other")
        assert load_tasks(initialized, project="other") == tasks
        assert load_tasks(initialized) == []  # default project still empty

    def test_tasks_isolated_per_project(self, initialized: Path) -> None:
        create_project(initialized, "proj2")
        t1 = Task(id="aaaa", description="in default")
        t2 = Task(id="bbbb", description="in proj2")
        save_tasks(initialized, [t1])
        save_tasks(initialized, [t2], project="proj2")
        assert load_tasks(initialized) == [t1]
        assert load_tasks(initialized, project="proj2") == [t2]

    def test_loads_active_project_after_switch(self, initialized: Path) -> None:
        create_project(initialized, "alt")
        set_active(initialized, "alt")
        t = Task(id="aaaa", description="alt task")
        save_tasks(initialized, [t])
        assert load_tasks(initialized) == [t]
        # original default project unaffected
        set_active(initialized, DEFAULT_PROJECT)
        assert load_tasks(initialized) == []


# --------------------------------------------------------------------------
# schema v3 (still current)
# --------------------------------------------------------------------------
class TestSchemaV3:
    def test_save_emits_version_3(self, initialized: Path) -> None:
        save_tasks(initialized, [Task(id="aaaa", description="one")])
        payload = json.loads(_state_path(initialized).read_text())
        assert payload["version"] == 3

    def test_save_includes_tags(self, initialized: Path) -> None:
        task = Task(id="aaaa", description="one", tags=["feature"])
        save_tasks(initialized, [task])
        payload = json.loads(_state_path(initialized).read_text())
        assert payload["tasks"][0]["tags"] == ["feature"]

    def test_load_v2_file_migrates_tags(self, initialized: Path) -> None:
        """A version:2 file without tags must load cleanly with tags=[]."""
        v2_payload = {
            "version": 2,
            "tasks": [
                {
                    "id": "a1b2",
                    "description": "old task",
                    "status": "Todo",
                    "created_at": "2026-06-15T10:00:00+00:00",
                    "depends_on": [],
                }
            ],
        }
        _state_path(initialized).write_text(json.dumps(v2_payload))
        tasks = load_tasks(initialized)
        assert len(tasks) == 1
        assert tasks[0].tags == []

    def test_load_v1_file_migrates_both(self, initialized: Path) -> None:
        """A version:1 file without depends_on/tags must load cleanly."""
        v1_payload = {
            "version": 1,
            "tasks": [
                {
                    "id": "a1b2",
                    "description": "old task",
                    "status": "Todo",
                    "created_at": "2026-06-15T10:00:00+00:00",
                }
            ],
        }
        _state_path(initialized).write_text(json.dumps(v1_payload))
        tasks = load_tasks(initialized)
        assert tasks[0].depends_on == []
        assert tasks[0].tags == []

    def test_roundtrip_with_tags(self, initialized: Path) -> None:
        tasks = [Task(id="aaaa", description="one", tags=["alpha", "beta"])]
        save_tasks(initialized, tasks)
        loaded = load_tasks(initialized)
        assert loaded[0].tags == ["alpha", "beta"]


class TestSchemaV2:
    def test_save_emits_version_3(self, initialized: Path) -> None:
        save_tasks(initialized, [Task(id="aaaa", description="one")])
        payload = json.loads(_state_path(initialized).read_text())
        assert payload["version"] == 3

    def test_save_includes_depends_on(self, initialized: Path) -> None:
        task = Task(id="aaaa", description="one", depends_on=["bbbb"])
        save_tasks(initialized, [task])
        payload = json.loads(_state_path(initialized).read_text())
        assert payload["tasks"][0]["depends_on"] == ["bbbb"]

    def test_load_v1_file_migrates_depends_on(self, initialized: Path) -> None:
        v1_payload = {
            "version": 1,
            "tasks": [
                {
                    "id": "a1b2",
                    "description": "old task",
                    "status": "Todo",
                    "created_at": "2026-06-15T10:00:00+00:00",
                }
            ],
        }
        _state_path(initialized).write_text(json.dumps(v1_payload))
        tasks = load_tasks(initialized)
        assert tasks[0].depends_on == []

    def test_roundtrip_with_depends_on(self, initialized: Path) -> None:
        tasks = [
            Task(id="aaaa", description="one", depends_on=["bbbb"]),
            Task(id="bbbb", description="two"),
        ]
        save_tasks(initialized, tasks)
        loaded = load_tasks(initialized)
        assert loaded[0].depends_on == ["bbbb"]
        assert loaded[1].depends_on == []


# --------------------------------------------------------------------------
# generate_id / find_task (unchanged domain logic, verify still works)
# --------------------------------------------------------------------------
class TestGenerateId:
    def test_format_is_4_hex(self) -> None:
        new = generate_id(set())
        assert len(new) == 4
        int(new, 16)

    def test_avoids_existing(self) -> None:
        existing = {generate_id(set()) for _ in range(50)}
        for _ in range(200):
            new = generate_id(existing)
            assert new not in existing

    def test_widens_when_4hex_exhausted(self) -> None:
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
