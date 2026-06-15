# AGENTS.md

`trackr` — per-repo CLI task tracker. Tasks in `.tasks/state.json` at repo root (Git-style). Typer + Rich, uv, Python 3.10+.

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
├── storage.py    # .tasks/ discovery, JSON persistence, ID gen. Returns data, never prints.
└── cli.py        # Typer app: parsing + Rich output + error handling. Thin.
```

Dep direction (never invert): `cli -> storage -> models -> errors`.

## Invariants

- **Storage:** `<repo-root>/.tasks/state.json`. Constants: `STORE_DIRNAME`, `STATE_FILENAME`.
- **Schema:** `{"version": 1, "tasks": [{id, description, status, created_at}]}`. Changing: bump `STATE_VERSION`, migrate in `load_tasks`, add load-old-file test.
- **Atomic writes only:** temp file + fsync + `os.replace`. Never write `state.json` in place.
- **Task IDs:** 4-char hex, collision-checked, widen on saturation. Matched case-insensitively.
- **Status** persisted verbatim (`Todo`/`In Progress`/`Done`); input coerced via `Status.coerce`.
- **`Status` is `class Status(str, Enum)`** — NOT `StrEnum` (keeps Python 3.10 support).
- `list` hides `Done` unless `--all/-a`.
- Subcommands (except `init`) resolve repo via `find_repo_root()` — must work from any subdir.

## Commands

```bash
uv sync                  # install deps
uv run pytest            # full suite (must pass)
uv run pytest -k <expr>  # focused run during TDD
uv run trackr <args>     # run CLI from source
```

Or use `just` (run `just` to list recipes). Wraps the same commands:
`just sync`, `just test`, `just check`, `just build`, `just install`.

## When adding a command

Logic in `storage.py`/`models.py`, thin command in `cli.py`, new failures as `TrackrError` subclasses, `@handle_errors` decorator, state writes via `save_tasks`. Test happy + error paths, assert persisted `state.json`. Update `docs/usage.md` and `README.md` in same change — public contract, keep in sync.
