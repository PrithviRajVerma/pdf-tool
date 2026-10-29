"""pdf-tool CLI — split command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pdf_tool.adapters.split import SplitAdapter
from pdf_tool.exceptions import PdfToolError
from pdf_tool.utils.config import get_config
from pdf_tool.utils.progress import conversion_spinner

console = Console()
app = typer.Typer()


@app.command("split")
def split(
    file: Annotated[Path, typer.Argument(help="PDF file to split.")],
    spec: Annotated[
        str | None,
        typer.Argument(help="Optional page range (e.g. '1-3,5') or chunk size (e.g. '2')."),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir", "-o", help="Directory for output PDFs. [default: from config or '.']"
        ),
    ] = None,
    pages: Annotated[
        str | None,
        typer.Option("--pages", help="Page range to extract, e.g. '1-3,5'."),
    ] = None,
    every: Annotated[
        int | None,
        typer.Option("--every", help="Split into chunks of N pages."),
    ] = None,
) -> None:
    """Split a PDF by page range or into equal-sized chunks."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: '{file}'")
        raise typer.Exit(1)

    config = get_config()
    if output_dir is None:
        cfg_out = config.get("defaults.output_dir", "")
        actual_output_dir = Path(cfg_out) if cfg_out else Path(".")
    else:
        actual_output_dir = output_dir

    # Infer from positional spec if --pages/--every not passed
    if spec is not None and pages is None and every is None:
        if spec.isdigit():
            every = int(spec)
        else:
            pages = spec

    if pages and every:
        console.print("[red]Error:[/red] --pages and --every are mutually exclusive.")
        raise typer.Exit(1)

    adapter = SplitAdapter()

    with conversion_spinner(f"Splitting '{file.name}' …"):
        try:
            outputs = adapter.split(file, actual_output_dir, page_range=pages, every=every)
        except PdfToolError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    console.print(f"[green]✅ Split into {len(outputs)} file(s) → {actual_output_dir}[/green]")
    for out in outputs:
        console.print(f"   {out.name}")
