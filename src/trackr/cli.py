"""Command-line interface for trackr (built with Typer + Rich)."""

from __future__ import annotations

import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from trackr import __version__
from trackr.errors import (
    CircularDependency,
    EmptyDescription,
    NotLinked,
    SelfDependency,
    TaskNotFound,
    TrackrError,
)
from trackr.models import Status, Task, is_blocked, open_blockers, would_cycle
from trackr.storage import (
    find_repo_root,
    find_task,
    generate_id,
    init_store,
    load_tasks,
    save_tasks,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A per-repository CLI task tracker (Git-style local state).",
)

console = Console()
err_console = Console(stderr=True)

# Status display colors for the table.
_STATUS_STYLE = {
    Status.TODO: "yellow",
    Status.IN_PROGRESS: "cyan",
    Status.DONE: "green",
}


def handle_errors(func: Callable) -> Callable:
    """Decorator: turn any :class:`TrackrError` into a clean exit(1).

    Keeps command bodies free of try/except boilerplate while ensuring users
    never see a raw traceback for an expected failure.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TrackrError as exc:
            err_console.print(f"[bold red]Error:[/] {exc}")
            raise typer.Exit(code=1) from exc

    return wrapper


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"trackr {__version__}")
        raise typer.Exit()


@app.callback()
def _main(
    _version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show the version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """trackr root callback (hosts the global --version flag)."""


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------
@app.command()
@handle_errors
def init() -> None:
    """Initialize the task tracker in the current directory."""
    store, created = init_store(Path.cwd())
    rel = store.relative_to(Path.cwd()) if store.is_relative_to(Path.cwd()) else store
    if created:
        console.print(
            f"[green]Initialized empty task tracker in[/] [bold]{rel}/[/]"
        )
    else:
        console.print(
            f"[yellow]Already a trackr repository[/] (found [bold]{rel}/[/]). "
            "Nothing to do."
        )


# --------------------------------------------------------------------------
# add
# --------------------------------------------------------------------------
@app.command()
@handle_errors
def add(
    description: str = typer.Argument(..., help="The task description."),
) -> None:
    """Add a new task (status defaults to 'Todo')."""
    desc = description.strip()
    if not desc:
        raise EmptyDescription()

    root = find_repo_root()
    tasks = load_tasks(root)
    new_id = generate_id({t.id for t in tasks})
    task = Task(id=new_id, description=desc)
    tasks.append(task)
    save_tasks(root, tasks)

    console.print(
        f"[green]Added task[/] [bold]{task.id}[/]: {task.description} "
        f"[dim]({task.status})[/]"
    )


# --------------------------------------------------------------------------
# list
# --------------------------------------------------------------------------
@app.command(name="list")
@handle_errors
def list_tasks(
    show_all: bool = typer.Option(
        False, "--all", "-a", help="Include tasks marked 'Done'."
    ),
) -> None:
    """List tasks in a table (hides 'Done' tasks unless --all)."""
    root = find_repo_root()
    tasks = load_tasks(root)

    visible = tasks if show_all else [t for t in tasks if t.status is not Status.DONE]

    if not tasks:
        console.print("[dim]No tasks yet. Add one with[/] [bold]trackr add \"...\"[/]")
        return
    if not visible:
        console.print(
            "[dim]No open tasks. Use[/] [bold]trackr list --all[/] "
            "[dim]to see completed ones.[/]"
        )
        return

    table = Table(title=None, header_style="bold", expand=False)
    table.add_column("ID", style="bold", no_wrap=True)
    table.add_column("Description")
    table.add_column("Status", no_wrap=True)
    table.add_column("Deps", no_wrap=True)
    table.add_column("Created", no_wrap=True)

    for task in visible:
        style = _STATUS_STYLE.get(task.status, "white")
        blockers = open_blockers(task, tasks)
        if blockers:
            n = len(blockers)
            deps_cell = Text(f"⊘ blocked ({n})", style="dim red")
        elif task.depends_on:
            deps_cell = Text("✓ clear", style="dim green")
        else:
            deps_cell = Text("—", style="dim")

        table.add_row(
            task.id,
            task.description,
            f"[{style}]{task.status}[/]",
            deps_cell,
            task.created_display(),
        )

    console.print(table)
    shown, total = len(visible), len(tasks)
    hidden = total - shown
    summary = f"{shown} task(s)"
    if hidden and not show_all:
        summary += f" ([dim]{hidden} done hidden[/])"
    console.print(summary)


# --------------------------------------------------------------------------
# status
# --------------------------------------------------------------------------
@app.command()
@handle_errors
def status(
    task_id: str = typer.Argument(..., help="The ID of the task to update."),
    new_status: str = typer.Argument(
        ..., help="New status: Todo | In Progress | Done (aliases allowed)."
    ),
) -> None:
    """Update a task's status."""
    target = Status.coerce(new_status)  # raises InvalidStatus on bad input

    root = find_repo_root()
    tasks = load_tasks(root)
    task = find_task(tasks, task_id)
    if task is None:
        raise TaskNotFound(task_id)

    previous = task.status
    if previous is target:
        console.print(
            f"[yellow]Task[/] [bold]{task.id}[/] is already [bold]{target}[/]."
        )
        return

    # Warn (but allow) when moving to In Progress or Done with open blockers.
    if target in (Status.IN_PROGRESS, Status.DONE):
        blockers = open_blockers(task, tasks)
        if blockers:
            ids = ", ".join(b.id for b in blockers)
            console.print(
                f"[yellow]Warning:[/] task [bold]{task.id}[/] still has open "
                f"blocker(s): [bold]{ids}[/]. Proceeding anyway."
            )

    task.status = target
    save_tasks(root, tasks)
    console.print(
        f"[green]Updated[/] [bold]{task.id}[/]: "
        f"[dim]{previous}[/] -> [bold]{target}[/]"
    )


# --------------------------------------------------------------------------
# remove
# --------------------------------------------------------------------------
@app.command()
@handle_errors
def remove(
    task_id: str = typer.Argument(..., help="The ID of the task to delete."),
) -> None:
    """Delete a task from the tracker."""
    root = find_repo_root()
    tasks = load_tasks(root)
    task = find_task(tasks, task_id)
    if task is None:
        raise TaskNotFound(task_id)

    canonical = task.id.lower()
    tasks = [t for t in tasks if t.id != task.id]

    # Auto-clean dangling references from dependents.
    cleaned: list[str] = []
    for t in tasks:
        if canonical in [d.lower() for d in t.depends_on]:
            t.depends_on = [d for d in t.depends_on if d.lower() != canonical]
            cleaned.append(t.id)

    save_tasks(root, tasks)
    console.print(
        f"[green]Removed task[/] [bold]{task.id}[/]: {task.description}"
    )
    if cleaned:
        affected = ", ".join(cleaned)
        console.print(
            f"[yellow]Warning:[/] removed dependency reference from task(s): "
            f"[bold]{affected}[/]"
        )


# --------------------------------------------------------------------------
# link
# --------------------------------------------------------------------------
@app.command()
@handle_errors
def link(
    task_id: str = typer.Argument(..., help="The task that will depend on another."),
    blocker_id: str = typer.Argument(..., help="The task that must finish first."),
) -> None:
    """Mark TASK_ID as depending on BLOCKER_ID (TASK_ID is blocked by BLOCKER_ID)."""
    root = find_repo_root()
    tasks = load_tasks(root)

    dependent = find_task(tasks, task_id)
    if dependent is None:
        raise TaskNotFound(task_id)

    blocker = find_task(tasks, blocker_id)
    if blocker is None:
        raise TaskNotFound(blocker_id)

    if dependent.id.lower() == blocker.id.lower():
        raise SelfDependency(dependent.id)

    if blocker.id.lower() in [d.lower() for d in dependent.depends_on]:
        console.print(
            f"[yellow]Task[/] [bold]{dependent.id}[/] already depends on "
            f"[bold]{blocker.id}[/]. Nothing to do."
        )
        return

    if would_cycle(tasks, dependent.id, blocker.id):
        raise CircularDependency(dependent.id, blocker.id)

    dependent.depends_on.append(blocker.id)
    save_tasks(root, tasks)
    console.print(
        f"[green]Linked:[/] [bold]{dependent.id}[/] now depends on "
        f"[bold]{blocker.id}[/]"
    )


# --------------------------------------------------------------------------
# unlink
# --------------------------------------------------------------------------
@app.command()
@handle_errors
def unlink(
    task_id: str = typer.Argument(..., help="The dependent task."),
    blocker_id: str = typer.Argument(..., help="The blocker task to remove."),
) -> None:
    """Remove a dependency between two tasks."""
    root = find_repo_root()
    tasks = load_tasks(root)

    dependent = find_task(tasks, task_id)
    if dependent is None:
        raise TaskNotFound(task_id)

    blocker = find_task(tasks, blocker_id)
    if blocker is None:
        raise TaskNotFound(blocker_id)

    canonical = blocker.id.lower()
    if canonical not in [d.lower() for d in dependent.depends_on]:
        raise NotLinked(dependent.id, blocker.id)

    dependent.depends_on = [d for d in dependent.depends_on if d.lower() != canonical]
    save_tasks(root, tasks)
    console.print(
        f"[green]Unlinked:[/] [bold]{dependent.id}[/] no longer depends on "
        f"[bold]{blocker.id}[/]"
    )


# --------------------------------------------------------------------------
# show
# --------------------------------------------------------------------------
@app.command()
@handle_errors
def show(
    task_id: str = typer.Argument(..., help="The ID of the task to inspect."),
) -> None:
    """Show full details for a single task, including dependencies."""
    root = find_repo_root()
    tasks = load_tasks(root)
    task = find_task(tasks, task_id)
    if task is None:
        raise TaskNotFound(task_id)

    style = _STATUS_STYLE.get(task.status, "white")

    # Age calculation
    try:
        created_dt = datetime.fromisoformat(task.created_at)
        now = datetime.now(timezone.utc)
        delta = now - created_dt
        days = delta.days
        age = f"{days}d ago" if days > 0 else "today"
    except ValueError:
        age = ""

    lines: list[str] = [
        f"[bold]ID:[/]          {task.id}",
        f"[bold]Description:[/] {task.description}",
        f"[bold]Status:[/]      [{style}]{task.status}[/]",
        f"[bold]Created:[/]     {task.created_display()}"
        + (f"  [dim]({age})[/]" if age else ""),
    ]

    # Depends on
    index = {t.id.lower(): t for t in tasks}
    if task.depends_on:
        lines.append("")
        lines.append("[bold]Depends on:[/]")
        for dep_id in task.depends_on:
            dep = index.get(dep_id.lower())
            if dep:
                dep_style = _STATUS_STYLE.get(dep.status, "white")
                marker = " [dim red](open)[/]" if dep.status is not Status.DONE else ""
                lines.append(
                    f"  [bold]{dep.id}[/]  [{dep_style}]{dep.status}[/]  "
                    f"{dep.description}{marker}"
                )
            else:
                lines.append(f"  [dim]{dep_id} (deleted)[/]")
    else:
        lines.append("")
        lines.append("[bold]Depends on:[/]  [dim]none[/]")

    # Blocks (reverse direction)
    blocks = [t for t in tasks if task.id.lower() in [d.lower() for d in t.depends_on]]
    if blocks:
        lines.append("")
        lines.append("[bold]Blocks:[/]")
        for b in blocks:
            b_style = _STATUS_STYLE.get(b.status, "white")
            lines.append(
                f"  [bold]{b.id}[/]  [{b_style}]{b.status}[/]  {b.description}"
            )
    else:
        lines.append("[bold]Blocks:[/]      [dim]nothing[/]")

    # Blocked warning
    if is_blocked(task, tasks):
        blockers = open_blockers(task, tasks)
        ids = ", ".join(b.id for b in blockers)
        lines.append("")
        lines.append(f"[bold red]⊘ Blocked[/] by: [bold]{ids}[/]")

    console.print(Panel("\n".join(lines), title=f"Task {task.id}", expand=False))


if __name__ == "__main__":  # pragma: no cover
    app()
