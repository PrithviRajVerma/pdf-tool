"""pdf-tool CLI — merge command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pdf_tool.adapters.merge import MergeAdapter
from pdf_tool.exceptions import PdfToolError
from pdf_tool.utils.output_validator import validate_pdf
from pdf_tool.utils.progress import conversion_spinner

console = Console()
app = typer.Typer()


@app.command("merge")
def merge(
    files: Annotated[list[Path], typer.Argument(help="PDF files to merge (in order).")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Output merged PDF path.")
    ] = None,
) -> None:
    """Merge multiple PDF files into a single PDF."""
    # Positional output support: pdf m a.pdf b.pdf out.pdf
    if (
        output is None
        and len(files) >= 3
        and not files[-1].exists()
        and files[-1].suffix.lower() == ".pdf"
    ):
        output = files[-1]
        files = files[:-1]
    elif output is None:
        output = Path("merged.pdf")

    if len(files) < 2:
        console.print("[red]Error:[/red] At least two PDF files are required.")
        raise typer.Exit(1)

    for f in files:
        if not f.exists():
            console.print(f"[red]Error:[/red] File not found: '{f}'")
            raise typer.Exit(1)

    adapter = MergeAdapter()

    with conversion_spinner(f"Merging {len(files)} PDFs …"):
        try:
            result = adapter.merge(files, output)
        except PdfToolError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    try:
        validate_pdf(result.output_path)
    except PdfToolError as exc:
        console.print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]✅ Merged {len(files)} PDFs → {result.output_path}[/green]")
    console.print(
        f"   Output size: {result.output_size_bytes:,} bytes  |  {result.duration_seconds:.2f}s"
    )
