# trackr — Usage Guide for Agents

This document is the **canonical reference for using `trackr`** from inside any
repository. It is written for AI agents (and humans) who need to track tasks
while working on a project, but who are *not* developing trackr itself.

`trackr` is a **per-repository CLI task tracker**. Task state lives in a hidden
`.tasks/` directory at the repo root — exactly like Git's `.git/`. Each repo has
its own independent task list, stored in a single `.tasks/state.json` file.

> **Keep this in sync.** When trackr's features change, update this file (see
> the maintenance note at the end and `AGENTS.md`).

---

## 1. Mental model

- **One store per repo.** The store is `<repo-root>/.tasks/state.json`.
- **Git-style discovery.** Every command except `init` walks up parent
  directories until it finds a `.tasks/` dir, so commands work from **any
  subdirectory** of the repo.
- **A task** has: a short `id`, a `description`, a `status`, and a `created_at`
  timestamp.
- **Three statuses:** `Todo` → `In Progress` → `Done`.
- **Local-first.** Nothing leaves the machine. No network, no daemon, no config.

---

## 2. Invoking the CLI

Depending on how the project is set up, one of these will work:

```bash
trackr <args>                       # if installed on PATH (uv tool install .)
uv run trackr <args>                # from within the trackr project dir
uv run --project /path/to/trackr trackr <args>   # from any other directory
python -m trackr <args>             # module entry, if importable
```

Throughout this doc, commands are shown as `trackr <args>`. Substitute whichever
invocation your environment supports.

Global flags:

| Flag | Effect |
| --- | --- |
| `--version`, `-V` | Print `trackr <version>` and exit. |
| `--help` | Show help. Running with no command also prints help. |

---

## 3. Quick start

```bash
trackr init                          # create .tasks/ in the current repo root
trackr add "Write integration tests" # add a task (status defaults to Todo)
trackr list                          # show open tasks (Done hidden)
trackr status a3f9 "In Progress"     # advance a task by its ID
trackr status a3f9 done              # mark it Done (alias accepted)
trackr list --all                    # show everything, including Done
trackr remove a3f9                   # delete a task
```

---

## 4. Commands

### `trackr init`

Initialize the tracker in the **current directory**. Creates
`./.tasks/state.json`.

- Idempotent: if a `.tasks/` already exists, it prints a notice and changes
  nothing (still exit code `0`).
- This is the **only** command that does not search parent dirs — it always
  acts on the current working directory.

```bash
trackr init
# -> Initialized empty task tracker in .tasks/
```

### `trackr add "<description>"`

Add a new task. Auto-assigns a unique 4-char hex ID; status starts as `Todo`.

- The description is **trimmed**; a blank/whitespace-only description is rejected
  (exit `1`).
- Wrap multi-word descriptions in quotes so the shell passes them as one arg.

```bash
trackr add "Refactor the auth module"
# -> Added task 7b2e: Refactor the auth module (Todo)
```

### `trackr list [--all | -a]`

List tasks in a table with columns: **ID, Description, Status, Created**.

- By default, **`Done` tasks are hidden**. Pass `--all` / `-a` to include them.
- Prints a summary line, e.g. `3 task(s) (2 done hidden)`.
- Empty states are handled gracefully (no tasks yet / no open tasks).

```bash
trackr list          # open tasks only
trackr list --all    # all tasks, including Done
```

### `trackr status <id> <new_status>`

Update a task's status. The status argument is **case-insensitive** and accepts
aliases (see §5).

- If the task is already in the requested status, it's a no-op with a notice
  (exit `0`).
- Unknown ID → exit `1`. Unrecognized status string → exit `1`.

```bash
trackr status 7b2e "in progress"
trackr status 7b2e wip          # same thing via alias
trackr status 7b2e done
```

### `trackr remove <id>`

Delete a task permanently from the store.

- Unknown ID → exit `1`.

```bash
trackr remove 7b2e
# -> Removed task 7b2e: Refactor the auth module
```

---

## 5. Status values & aliases

Three canonical statuses are stored **verbatim**: `Todo`, `In Progress`, `Done`.
Input is normalized (lowercased, whitespace collapsed) and matched against this
alias table:

| Canonical (stored) | Accepted input (case-insensitive) |
| --- | --- |
| `Todo` | `todo`, `to do`, `td`, `open`, `new` |
| `In Progress` | `in progress`, `inprogress`, `progress`, `wip`, `ip`, `doing`, `started` |
| `Done` | `done`, `complete`, `completed`, `finished`, `closed` |

Anything outside this table is rejected with: `Invalid status '<x>'. Valid
statuses: Todo, In Progress, Done.`

---

## 6. Task IDs

- IDs are **4 hex characters** (e.g. `a3f9`, `7b2e`), generated randomly and
  checked for uniqueness within the repo.
- IDs are matched **case-insensitively** — `A3F9` and `a3f9` refer to the same
  task.
- To learn a task's ID, run `trackr list` (or `list --all`).

---

## 7. Storage & schema

Layout:

```
<repo-root>/
└── .tasks/
    └── state.json
```

`state.json` schema (current `version: 1`):

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

Notes for agents that read/inspect this file:

- `status` is one of the exact strings `"Todo"`, `"In Progress"`, `"Done"`.
- `created_at` is a **second-precision UTC ISO-8601** timestamp. The `list`
  table displays only the `YYYY-MM-DD` date.
- Writes are **atomic** (temp file + `os.replace`), so the file is never left
  half-written.
- **Prefer the CLI over hand-editing** `state.json`. If you must read it, treat
  it as read-only; let `trackr` perform mutations.

### Committing task state

`.tasks/` is normal repo content for downstream projects — **commit it** so the
task list is shared/versioned with the code. (It is gitignored only inside
trackr's *own* source repo, which uses it as dev scratch state.)

---

## 8. Exit codes & error handling

- **`0`** — success (including idempotent no-ops like re-`init` or setting a
  status that's already set).
- **`1`** — any expected, user-facing error. trackr prints a clean
  `Error: <message>` line (never a Python traceback).

Common error conditions:

| Situation | Message (abridged) |
| --- | --- |
| Command run outside a trackr repo | `Not a trackr repository (no .tasks/ directory found). Run 'trackr init' first.` |
| Unknown task ID | `No task found with ID '<id>'.` |
| Bad status string | `Invalid status '<x>'. Valid statuses: Todo, In Progress, Done.` |
| Empty `add` description | `Task description must not be empty.` |
| Corrupt/unreadable `state.json` | `State file at '<path>' is corrupt or unreadable. ...` |

Agents should branch on the **exit code** (`0` vs `1`) and surface the printed
message when a command fails.

---

## 9. Recommended agent workflow

1. **Ensure a store exists.** Run `trackr init` once at the repo root (safe to
   run again — it's idempotent).
2. **Record work** as you plan it: `trackr add "<concrete, actionable task>"`.
3. **Discover IDs** with `trackr list` before updating/removing.
4. **Reflect progress:** move tasks to `In Progress` when you start them and
   `Done` when finished.
5. **Review** open work with `trackr list`; use `--all` for an audit including
   completed tasks.
6. **Commit `.tasks/`** alongside your code changes so the task history travels
   with the repo.

---

## 10. Maintenance

This doc must mirror the actual CLI. Whenever a trackr command, flag, status
alias, schema field, or error is **added, removed, or changed**, update:

- the relevant section here (`docs/usage.md`),
- the command/alias tables in `README.md`.

See `AGENTS.md` → "Documentation upkeep" for the binding rule.
