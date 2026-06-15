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
trackr list                          # show open tasks (hides Done)
trackr list --all                    # show everything, including Done
trackr status a3f9 "In Progress"     # update status (aliases ok: wip, done...)
trackr status a3f9 done
trackr remove a3f9                   # delete a task
trackr --version
```

### Commands

| Command | Description |
| --- | --- |
| `init` | Initialize the tracker in the current directory. |
| `add "<desc>"` | Add a task; auto-assigns a short ID, status `Todo`. |
| `list [--all/-a]` | List tasks in a table. Hides `Done` unless `--all`. |
| `status <id> <status>` | Set status to `Todo`, `In Progress`, or `Done`. |
| `remove <id>` | Delete a task. |

### Status aliases

| Canonical | Accepted input (case-insensitive) |
| --- | --- |
| `Todo` | `todo`, `to do`, `td`, `open`, `new` |
| `In Progress` | `in progress`, `inprogress`, `progress`, `wip`, `ip`, `doing`, `started` |
| `Done` | `done`, `complete`, `completed`, `finished`, `closed` |

## Storage layout

```
your-repo/
└── .tasks/
    └── state.json
```

`state.json`:

```json
{
  "version": 1,
  "tasks": [
    {
      "id": "a3f9",
      "description": "Write the README",
      "status": "Todo",
      "created_at": "2026-06-15T10:30:00+00:00"
    }
  ]
}
```

## Development

```bash
uv sync
uv run python -m trackr --help   # run via module
```

## License

MIT
