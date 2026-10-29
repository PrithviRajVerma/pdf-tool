"""pdf-tool CLI — compress command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pdf_tool.adapters.compress import CompressAdapter
from pdf_tool.exceptions import PdfToolError
from pdf_tool.utils.config import get_config
from pdf_tool.utils.output_validator import validate_pdf
from pdf_tool.utils.progress import conversion_spinner

console = Console()
app = typer.Typer()

_VALID_LEVELS = {"high", "medium", "low"}


@app.command("compress")
def compress(
    file: Annotated[Path, typer.Argument(help="PDF file to compress.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output compressed PDF path."),
    ] = None,
    level: Annotated[
        str | None,
        typer.Option(
            "--level", help="Compression level: high, medium, low. [default: from config]"
        ),
    ] = None,
) -> None:
    """Compress a PDF file using Ghostscript (or pypdf fallback)."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: '{file}'")
        raise typer.Exit(1)

    config = get_config()
    actual_level = (level or config.get("defaults.compression_level", "medium")).lower()

    if actual_level not in _VALID_LEVELS:
        console.print(
            f"[red]Error:[/red] Invalid level '{actual_level}'. Choose: high, medium, low."
        )
        raise typer.Exit(1)

    out_path = output or file.with_stem(file.stem + "_compressed").with_suffix(".pdf")
    adapter = CompressAdapter()

    with conversion_spinner(f"Compressing '{file.name}' (level={actual_level}) …"):
        try:
            result = adapter.compress(file, out_path, level=actual_level)
        except PdfToolError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    try:
        validate_pdf(result.output_path)
    except PdfToolError as exc:
        console.print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    delta = result.input_size_bytes - result.output_size_bytes
    pct = (delta / result.input_size_bytes * 100) if result.input_size_bytes else 0
    console.print(f"[green]✅ Compressed → {result.output_path}[/green]")
    console.print(
        f"   {_fmt_bytes(result.input_size_bytes)} → {_fmt_bytes(result.output_size_bytes)}"
        f"  (saved {_fmt_bytes(delta)}, {pct:.1f}%)  |  engine: {result.engine}  |  {result.duration_seconds:.2f}s"
    )


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
