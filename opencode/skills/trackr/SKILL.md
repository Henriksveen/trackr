---
name: trackr
description: Per-repo CLI task tracker. Use when working in a repo that has a .tasks/ directory, or when the user asks to track tasks, manage todos, update task status, log progress, or use trackr. Provides full usage: commands, status aliases, IDs, schema, workflow loop.
---

## What I do

`trackr` is a per-repo CLI task tracker. State lives in `.tasks/state.json` at the repo root (Git-style discovery — works from any subdir). Tasks have: `id` (4-char hex), `description`, `status` (`Todo` / `In Progress` / `Done`), `created_at`, `depends_on` (list of blocker IDs), `tags` (list of free-form label strings).

---

## What counts as a task

A task is **one project-meeting bullet** — a meaningful, independently-shippable chunk of work (a feature, a migration, a milestone). Not a step toward one.

**Sizing heuristic:** if it's something you'd tick off a personal checklist during an afternoon of coding, it is too small. It belongs *inside* a task, not as one.

**Anti-decomposition rule:** never create separate tasks for the implementation steps of a single feature. Writing tests, bumping the schema, editing a model, adding a CLI flag, updating docs — these are *how you do a task*, not tasks themselves. Keep TDD steps and sub-steps in your own session todo list. Do not put them in trackr.

| Track it in trackr | Do NOT create as a task |
|---|---|
| `Implement tags feature` | `Write failing tests for tags` |
| `Add dependency graph to list output` | `Bump schema to v3` |
| `Migrate storage to atomic writes` | `Add --tags flag to add command` |
| `Add auth module` | `Update SKILL.md and README` |

trackr = the project board (milestones). Your in-session todo list = implementation steps. Keep the layers separate.

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

### `trackr add "<description>" [--tags t1,t2]`
Add a task. Auto-assigns a unique 4-char hex ID; status starts as `Todo`. Blank/whitespace description rejected (exit 1). Optional `--tags` accepts a comma-separated list of labels.
```bash
trackr add "Refactor auth module"
# -> Added task 7b2e: Refactor auth module (Todo)
trackr add "Fix login bug" --tags "bug,urgent"
# -> Added task 3c1a: Fix login bug (Todo) (bug, urgent)
```

### `trackr list [--all | -a] [--tag <label>]`
List tasks in a table (ID, Description, Status, Tags, Deps, Created). `Done` tasks hidden by default; `--all` includes them. `--tag` filters to tasks carrying that label (repeatable; any-match). The **Deps** column shows:
- `⊘ blocked (N)` — has N open blocker(s)
- `✓ clear` — has deps but all are Done
- `—` — no dependencies
```bash
trackr list                          # open tasks only
trackr list --all                    # everything, including Done
trackr list --tag bug                # tasks tagged "bug"
trackr list --tag bug --tag urgent   # tasks tagged "bug" OR "urgent"
```

### `trackr status <id> <new_status>`
Update a task's status. Case-insensitive; accepts aliases (see below). No-op if already in that status (exit 0). Unknown ID or bad status → exit 1.
If the task has open blockers and the new status is `In Progress` or `Done`, a warning is printed but the update proceeds (warn-only, not blocked).
```bash
trackr status 7b2e "in progress"
trackr status 7b2e wip    # same via alias
trackr status 7b2e done
```

### `trackr remove <id>`
Delete a task permanently. If other tasks depend on the deleted task, their `depends_on` lists are cleaned automatically and a warning is printed. Unknown ID → exit 1.

### `trackr show <id>`
Show full detail for one task: ID, description, status, tags, created date + age, **Depends on** list (each blocker's id/status/description), **Blocks** list (reverse — tasks that depend on this one), and a blocked warning if applicable. Unknown ID → exit 1.
```bash
trackr show 7b2e
```

### `trackr tag <id> <label>`
Add a tag to a task. Unknown ID → exit 1. Duplicate tags are a silent no-op.
```bash
trackr tag 7b2e bug
```

### `trackr untag <id> <label>`
Remove a tag from a task. Unknown ID or tag not present → exit 1.
```bash
trackr untag 7b2e bug
```

### `trackr link <id> <blocker-id>`
Mark `<id>` as depending on `<blocker-id>` (`<blocker-id>` must finish before `<id>`). Rejected with exit 1 if: either ID unknown, self-link, or would create a cycle. Re-linking an existing dependency is a silent no-op (exit 0).
```bash
trackr link a3f9 b2c1   # a3f9 depends on b2c1
```

### `trackr unlink <id> <blocker-id>`
Remove a dependency. Exit 1 if either ID unknown or the link doesn't exist.
```bash
trackr unlink a3f9 b2c1
```

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
  "version": 3,
  "tasks": [
    {
      "id": "a3f9",
      "description": "Implement login feature",
      "status": "Todo",
      "created_at": "2026-06-15T10:30:00+00:00",
      "depends_on": ["b2c1"],
      "tags": ["auth", "backend"]
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

- `status` is one of the exact strings `"Todo"`, `"In Progress"`, `"Done"`.
- `depends_on` is a list of blocker task IDs (tasks that must be `Done` first).
- `tags` is a list of free-form label strings.
- Version 1 files (missing `depends_on`) and version 2 files (missing `tags`) load transparently; tasks get missing fields defaulted to `[]`.
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
| Self-dependency | `A task cannot depend on itself ('<id>').` |
| Circular dependency | `Circular dependency: linking '<dep>' -> '<blocker>' would create a cycle.` |
| Unlink not linked | `Task '<dep>' does not depend on '<blocker>'.` |
| Untag label not present | `Task '<id>' is not tagged '<label>'.` |

---

## Recommended workflow

1. `trackr init` — once at repo root (idempotent).
2. `trackr add "<milestone>"` — record each **milestone-sized** unit of work. Before adding, ask: *"Is this a project-meeting bullet, or a step toward one?"* Only add the former. Implementation steps (write tests, bump schema, edit a model, update docs) stay in your session todo list — not here.
3. `trackr link <id> <blocker-id>` — express ordering constraints **between milestones**.
4. `trackr list` — discover IDs and see blocked tasks.
5. `trackr show <id>` — inspect full dependency detail.
6. `trackr status <id> "In Progress"` — when you start a task.
7. `trackr status <id> done` — when finished.
8. `trackr list --all` — audit open + completed work.
9. Commit `.tasks/` with your code changes.
