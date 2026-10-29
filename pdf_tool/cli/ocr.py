"""pdf-tool CLI — ocr command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from pdf_tool.adapters.ocr import OcrAdapter
from pdf_tool.exceptions import MissingDependencyError, PdfToolError
from pdf_tool.utils.config import get_config
from pdf_tool.utils.output_validator import validate_pdf
from pdf_tool.utils.progress import conversion_spinner

console = Console()
app = typer.Typer()


@app.command("ocr")
def ocr(
    file: Annotated[Path, typer.Argument(help="Scanned PDF file to run OCR on.")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output searchable PDF path."),
    ] = None,
    lang: Annotated[
        str | None,
        typer.Option(
            "--lang",
            "-l",
            help="Tesseract language code (e.g. 'eng', 'fra'). [default: from config]",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force OCR even if searchable text already exists."),
    ] = False,
    deskew: Annotated[
        bool,
        typer.Option("--deskew/--no-deskew", help="Automatically deskew scanned pages."),
    ] = True,
) -> None:
    """Add a searchable, selectable text layer to a scanned PDF."""
    if not file.exists():
        console.print(f"[red]Error:[/red] File not found: '{file}'")
        raise typer.Exit(1)

    config = get_config()
    actual_lang = lang or config.get("defaults.ocr_language", "eng")

    out_path = output or file.with_stem(file.stem + "_ocr").with_suffix(".pdf")
    adapter = OcrAdapter()

    with conversion_spinner(f"Running OCR on '{file.name}' (lang={actual_lang}) …"):
        try:
            result = adapter.convert(
                file,
                out_path,
                lang=actual_lang,
                force=force,
                deskew=deskew,
            )
        except MissingDependencyError as exc:
            console.print(f"[red]Missing dependency:[/red] {exc}")
            if exc.install_hints:
                console.print("\n[yellow]Install Tesseract for your system:[/yellow]")
                for os_name, cmd in exc.install_hints.items():
                    console.print(f"  • {os_name}: [cyan]{cmd}[/cyan]")
            raise typer.Exit(1) from exc
        except PdfToolError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    try:
        validate_pdf(result.output_path)
    except PdfToolError as exc:
        console.print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"[green]✅ OCR Complete → {result.output_path}[/green]")
    console.print(
        f"   Size: {result.output_size_bytes:,} bytes  |  "
        f"Duration: {result.duration_seconds:.2f}s  |  "
        f"Engine: {result.engine}"
    )
