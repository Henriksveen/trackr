---
name: trackr
description: Per-repo CLI task tracker. Use when working in a repo that has a .tasks/ directory, or when the user asks to track tasks, manage todos, update task status, log progress, or use trackr. Provides full usage: commands, status aliases, IDs, schema, workflow loop.
---

## What I do

`trackr` is a per-repo CLI task tracker. State lives in `.tasks/state.json` at the repo root (Git-style discovery — works from any subdir). Tasks have: `id` (4-char hex), `description`, `status` (`Todo` / `In Progress` / `Done`), `created_at`.

---

## Invoking the CLI

```bash
trackr <args>                # if installed on PATH (uv tool install .)
uv run trackr <args>         # from within the trackr project dir
```

---

## Commands

### `trackr init`
Create `.tasks/state.json` in the current directory. Idempotent — safe to re-run.

### `trackr add "<description>"`
Add a task. Auto-assigns a unique 4-char hex ID; status starts as `Todo`. Blank/whitespace description rejected (exit 1).
```bash
trackr add "Refactor auth module"
# -> Added task 7b2e: Refactor auth module (Todo)
```

### `trackr list [--all | -a]`
List tasks in a table (ID, Description, Status, Created). `Done` tasks hidden by default; `--all` includes them. Prints summary line.
```bash
trackr list          # open tasks only
trackr list --all    # everything, including Done
```

### `trackr status <id> <new_status>`
Update a task's status. Case-insensitive; accepts aliases (see below). No-op if already in that status (exit 0). Unknown ID or bad status → exit 1.
```bash
trackr status 7b2e "in progress"
trackr status 7b2e wip    # same via alias
trackr status 7b2e done
```

### `trackr remove <id>`
Delete a task permanently. Unknown ID → exit 1.

---

## Status values & aliases

| Stored verbatim | Accepted input (case-insensitive) |
|---|---|
| `Todo` | `todo`, `to do`, `td`, `open`, `new` |
| `In Progress` | `in progress`, `inprogress`, `progress`, `wip`, `ip`, `doing`, `started` |
| `Done` | `done`, `complete`, `completed`, `finished`, `closed` |

---

## Task IDs

4 hex chars (e.g. `a3f9`), matched case-insensitively. Run `trackr list` to discover IDs.

---

## Storage & schema

```
<repo-root>/
└── .tasks/
    └── state.json
```

```json
{
  "version": 1,
  "tasks": [
    {
      "id": "a3f9",
      "description": "Write integration tests",
      "status": "Todo",
      "created_at": "2026-06-15T10:30:00+00:00"
    }
  ]
}
```

- `status` is one of the exact strings `"Todo"`, `"In Progress"`, `"Done"`.
- Writes are atomic (temp file + `os.replace`). Prefer CLI over hand-editing `state.json`.
- Commit `.tasks/` alongside code — task history travels with the repo.

---

## Exit codes

- `0` — success (including idempotent no-ops).
- `1` — user-facing error. trackr prints `Error: <message>` (never a traceback). Branch on exit code; surface the printed message on failure.

Common errors:

| Situation | Message |
|---|---|
| Run outside a trackr repo | `Not a trackr repository … Run 'trackr init' first.` |
| Unknown task ID | `No task found with ID '<id>'.` |
| Bad status string | `Invalid status '<x>'. Valid statuses: Todo, In Progress, Done.` |
| Empty description | `Task description must not be empty.` |

---

## Recommended workflow

1. `trackr init` — once at repo root (idempotent).
2. `trackr add "<task>"` — record work as you plan it.
3. `trackr list` — discover IDs before updating.
4. `trackr status <id> "In Progress"` — when you start a task.
5. `trackr status <id> done` — when finished.
6. `trackr list --all` — audit open + completed work.
7. Commit `.tasks/` with your code changes.
