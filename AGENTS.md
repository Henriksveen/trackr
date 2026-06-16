# AGENTS.md

`trackr` — per-repo CLI task tracker. Tasks in `.trackr/<project>.json` at repo root (Git-style). Typer + Rich, uv, Python 3.10+.

## Rules

- **TDD.** Failing test first, then implement to green. No feature/fix without test.
- **Keep layers separate** (see Architecture). No business logic in `cli.py`; no stdout in `storage.py`.
- **No raw tracebacks for user errors.** Raise `TrackrError` subclass; `@handle_errors` renders it.
- **Stdlib-first.** Runtime deps: typer, rich. Dev dep: pytest. Don't add more without reason.
- `uv run pytest` must be green before done.

## Architecture

```
src/trackr/
├── __init__.py   # __version__ (single source of truth)
├── errors.py     # TrackrError base + exceptions (each carries user-facing msg)
├── models.py     # Status enum + _ALIASES, Task dataclass. Pure domain.
├── storage.py    # .trackr/ discovery, JSON persistence, ID gen, project mgmt. Returns data, never prints.
└── cli.py        # Typer app: parsing + Rich output + error handling. Thin.
```

Dep direction (never invert): `cli -> storage -> models -> errors`.

## Invariants

- **Storage:** `<repo-root>/.trackr/<project>.json`. Constants: `STORE_DIRNAME`, `ACTIVE_FILENAME`, `DEFAULT_PROJECT`, `PROJECT_SUFFIX`. Active project pointer: `.trackr/active` (plain text, one line).
- **Schema:** `{"version": 3, "tasks": [{id, description, status, created_at, depends_on, tags}]}`. `depends_on` is a list of blocker IDs (strings). Version 1 files (no `depends_on`, no `tags`) and version 2 files (no `tags`) load transparently — tasks default missing fields to `[]`. Changing schema: bump `STATE_VERSION`, migrate in `load_tasks`, add load-old-file test.
- **Atomic writes only:** temp file + fsync + `os.replace`. Never write state files in place. Shared via `_atomic_write_text`.
- **Task IDs:** 4-char hex, collision-checked, widen on saturation. Matched case-insensitively.
- **Status** persisted verbatim (`Todo`/`In Progress`/`Done`); input coerced via `Status.coerce`.
- **`Status` is `class Status(str, Enum)`** — NOT `StrEnum` (keeps Python 3.10 support).
- `list` hides `Done` unless `--all/-a`.
- Subcommands (except `init`) resolve repo via `find_repo_root()` — must work from any subdir.
- **Project names:** `[A-Za-z0-9._-]+`, non-empty, not `active` (reserved). Validated via `_validate_project_name`.

## Commands

```bash
uv sync                  # install deps
uv run pytest            # full suite (must pass)
uv run pytest -k <expr>  # focused run during TDD
uv run trackr <args>     # run CLI from source
```

Or use `just` (run `just` to list recipes). Wraps the same commands:
`just sync`, `just test`, `just check`, `just build`, `just install`, `just install-opencode`.

## When adding a command

Logic in `storage.py`/`models.py`, thin command in `cli.py`, new failures as `TrackrError` subclasses, `@handle_errors` decorator, state writes via `save_tasks`. Test happy + error paths, assert persisted state file. Update `opencode/skills/trackr/SKILL.md` in the same change — it is the canonical public contract.

`opencode/skills/trackr/SKILL.md` is the **canonical agent-facing usage doc** for trackr. It ships via `just install-opencode` into `~/.config/opencode/skills/trackr/`. When any command, flag, status alias, schema field, or error message changes, update the skill in the same change. Update `README.md` only if the install steps or the usage command list change — README is intentionally minimal (install + usage only) and is not a mirror of the skill.

`opencode/agents/trackr.md` is a **primary opencode agent** that converts natural language input into trackr task operations (add, tag, link, status, remove, project list/new/switch/current, etc.) — no confirmation, executes directly. It ships via `just install-opencode` (into `~/.config/opencode/agents/`) and defers to the trackr skill for full CLI detail. Keep its verb list and granularity rule consistent with the skill when commands or the milestone contract change.

Skills provide specialized instructions and workflows for specific tasks.
Use the skill tool to load a skill when a task matches its description.
<available_skills>
  <skill>
    <name>trackr</name>
    <description>Per-repo CLI task tracker. Use when working in a repo that has a .trackr/ directory, or when the user asks to track tasks, manage todos, update task status, log progress, or use trackr. Provides full usage: commands, status aliases, IDs, schema, workflow loop.</description>
    <location>opencode/skills/trackr/SKILL.md</location>
  </skill>
</available_skills>
