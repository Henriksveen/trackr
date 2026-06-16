# trackr

A small, fast **per-repository CLI task tracker**. State is stored locally in a
hidden `.trackr/` directory at the repo root — just like Git's `.git/` — so each
repository keeps its own independent task list.

## Features

- Local-first: tasks live in `.trackr/<project>.json` at the repo root.
- Works from any subdirectory (walks up to find `.trackr/`, Git-style).
- Multiple projects per repo — switch between independent task groups with `trackr project switch`.
- Short, unique 4-char hex task IDs.
- Clean Rich-rendered table output.
- Case-insensitive status input with aliases (`wip`, `done`, `in progress`, ...).
- Atomic writes — the state file can't be corrupted by an interrupted save.
- Task dependencies — link tasks so one blocks another, with cycle detection.
- Task tags — label tasks with free-form tags; filter with `--tag`.

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) for dependency management

## Install

```bash
# from the project directory
uv sync

# run without installing
uv run trackr --help

# or install as a tool on your PATH
uv tool install .
trackr --help
```

## Task granularity

A task is **one project-meeting bullet** — a feature, a migration, a milestone. Not an implementation step.

If you'd put it on a personal afternoon checklist (*write tests*, *bump schema*, *update README*), it is too small. Those steps belong inside a task, not as separate tasks.

| Track it in trackr | Do NOT create as a task |
| --- | --- |
| `Implement tags feature` | `Write failing tests for tags` |
| `Add dependency graph to list output` | `Bump schema to v3` |
| `Migrate storage to atomic writes` | `Add --tags flag to add command` |
| `Add auth module` | `Update SKILL.md and README` |

trackr = the project board. Your in-session todo list = implementation steps. Keep the layers separate.

## Usage

```bash
trackr init                          # create .trackr/ in the current repo
trackr add "Write the README"        # add a task (status: Todo)
trackr add "Fix login bug" --tags "bug,urgent"  # add with tags
trackr list                          # show open tasks (hides Done)
trackr list --all                    # show everything, including Done
trackr list --tag bug                # filter by tag
trackr list --tag bug --tag urgent   # filter by multiple tags (any match)
trackr status a3f9 "In Progress"     # update status (aliases ok: wip, done...)
trackr status a3f9 done
trackr tag a3f9 feature              # add a tag
trackr untag a3f9 feature            # remove a tag
trackr remove a3f9                   # delete a task
trackr show a3f9                     # show full task detail + deps + tags
trackr link a3f9 b2c1                # a3f9 depends on b2c1 (b2c1 must finish first)
trackr unlink a3f9 b2c1             # remove that dependency
trackr --version
```

### Commands

| Command | Description |
| --- | --- |
| `init` | Initialize the tracker in the current directory. |
| `add "<desc>" [--tags t1,t2]` | Add a task; auto-assigns a short ID, status `Todo`. Optional comma-separated tags. |
| `list [--all/-a] [--tag t]` | List tasks in a table. Hides `Done` unless `--all`. Filter by tag with `--tag` (repeatable). |
| `status <id> <status>` | Set status to `Todo`, `In Progress`, or `Done`. |
| `tag <id> <label>` | Add a tag to a task. |
| `untag <id> <label>` | Remove a tag from a task. |
| `remove <id>` | Delete a task. |
| `show <id>` | Show full details: description, status, age, tags, deps, blocks. |
| `link <id> <blocker-id>` | Mark `<id>` as depending on `<blocker-id>`. |
| `unlink <id> <blocker-id>` | Remove that dependency. |

### Status aliases

| Canonical | Accepted input (case-insensitive) |
| --- | --- |
| `Todo` | `todo`, `to do`, `td`, `open`, `new` |
| `In Progress` | `in progress`, `inprogress`, `progress`, `wip`, `ip`, `doing`, `started` |
| `Done` | `done`, `complete`, `completed`, `finished`, `closed` |

### Dependencies

- `trackr link A B` means "A depends on B" — B must finish before A.
- The `list` table shows a **Deps** column: `⊘ blocked (N)` when open blockers exist, `✓ clear` when all blockers are done, `—` when no deps.
- **`list` output is sorted in pipeline order**: blockers appear above the tasks that depend on them. Tasks with no dependency relationship preserve their original insertion order. Edges to hidden (`Done`) tasks are ignored for ordering purposes. The stored order in `state.json` is never changed.
- Moving a blocked task to `In Progress` or `Done` is allowed but prints a warning listing open blockers.
- Deleting a blocker automatically removes it from all dependent tasks' `depends_on` lists and prints a warning.
- Linking to yourself, or creating a cycle (A→B→A), is rejected with exit code 1.
- Re-linking an already-existing dependency is a silent no-op (exit 0).

## Projects

Each repo can have multiple independent task groups called **projects**. The initial project is named `default`.

```bash
trackr project list               # list all projects (* marks the active one)
trackr project current            # print the active project name
trackr project new <name>         # create a new project (does not switch)
trackr project switch <name>      # switch the active project
```

All task commands (`add`, `list`, `status`, etc.) operate on the **active** project. To work with a different group, switch first:

```bash
trackr project new frontend
trackr project switch frontend
trackr add "Build navigation component"
trackr project switch default
```

Project names must use only `[A-Za-z0-9._-]` characters and must not be empty or `active`.

## Storage layout

```
your-repo/
└── .trackr/
    ├── active          # plain text — name of the active project
    ├── default.json    # default project state
    └── frontend.json   # another project (if created)
```

`default.json` (schema version 3):

```json
{
  "version": 3,
  "tasks": [
    {
      "id": "a3f9",
      "description": "Write the README",
      "status": "Todo",
      "created_at": "2026-06-15T10:30:00+00:00",
      "depends_on": ["b2c1"],
      "tags": ["docs", "urgent"]
    },
    {
      "id": "b2c1",
      "description": "Design the API",
      "status": "In Progress",
      "created_at": "2026-06-15T09:00:00+00:00",
      "depends_on": [],
      "tags": []
    }
  ]
}
```

Version 1 files (no `depends_on` field) and version 2 files (no `tags` field) are loaded transparently — old tasks get the missing fields defaulted to `[]`.

## Development

```bash
uv sync
uv run python -m trackr --help   # run via module
```

Recipes are also available via [`just`](https://just.systems) (run `just` to list them):

```bash
just sync     # install deps
just test     # run full test suite
just check    # sync + test (pre-commit gate)
just build    # build wheel + sdist
just install  # install trackr as a tool on PATH
just install-opencode  # copy skill + rule + planner agent into ~/.config/opencode/
```

## License

MIT
