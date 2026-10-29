"""Rich progress bar and spinner wrappers."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.spinner import Spinner
from rich.text import Text

console = Console()


@contextmanager
def conversion_spinner(description: str) -> Generator[Live, None, None]:
    """Context manager that displays a Rich spinner during a conversion.

    Args:
        description: Text to display next to the spinner.

    Yields:
        A :class:`rich.live.Live` instance (can be used to update the display).
    """
    spinner = Spinner("dots", text=Text(description, style="bold cyan"))
    with Live(spinner, console=console, refresh_per_second=10) as live:
        yield live


@contextmanager
def conversion_progress(total: int, description: str) -> Generator[Progress, None, None]:
    """Context manager that displays a Rich progress bar.

    Args:
        total: Total number of steps.
        description: Label shown next to the progress bar.

    Yields:
        A :class:`rich.progress.Progress` instance with a task already added.
        Callers should call ``progress.advance(task_id)`` to update.
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    )
    with progress:
        progress.add_task(description, total=total)
        yield progress
