"""Command-line interface for trackr (built with Typer + Rich)."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Callable, Optional

import typer
from rich.console import Console
from rich.table import Table

from trackr import __version__
from trackr.errors import EmptyDescription, TaskNotFound, TrackrError
from trackr.models import Status, Task
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
    table.add_column("Created", no_wrap=True)

    for task in visible:
        style = _STATUS_STYLE.get(task.status, "white")
        table.add_row(
            task.id,
            task.description,
            f"[{style}]{task.status}[/]",
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

    tasks = [t for t in tasks if t.id != task.id]
    save_tasks(root, tasks)
    console.print(
        f"[green]Removed task[/] [bold]{task.id}[/]: {task.description}"
    )


if __name__ == "__main__":  # pragma: no cover
    app()
