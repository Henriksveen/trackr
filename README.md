# trackr

A small, fast **per-repository CLI task tracker**. State is stored locally in a
hidden `.tasks/` directory at the repo root — just like Git's `.git/` — so each
repository keeps its own independent task list.

## Features

- Local-first: tasks live in `.tasks/state.json` at the repo root.
- Works from any subdirectory (walks up to find `.tasks/`, Git-style).
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

## Usage

```bash
trackr init                          # create .tasks/ in the current repo
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
- Moving a blocked task to `In Progress` or `Done` is allowed but prints a warning listing open blockers.
- Deleting a blocker automatically removes it from all dependent tasks' `depends_on` lists and prints a warning.
- Linking to yourself, or creating a cycle (A→B→A), is rejected with exit code 1.
- Re-linking an already-existing dependency is a silent no-op (exit 0).

## Storage layout

```
your-repo/
└── .tasks/
    └── state.json
```

`state.json` (schema version 3):

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
just install-opencode  # copy skill + rule into ~/.config/opencode/
```

## License

MIT
