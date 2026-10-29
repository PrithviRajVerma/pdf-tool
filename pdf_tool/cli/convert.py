"""pdf-tool CLI — convert command."""

from __future__ import annotations

import concurrent.futures
import glob
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

import pdf_tool.adapters  # noqa: F401
from pdf_tool.adapters.image_to_pdf import ImageToPdfAdapter
from pdf_tool.exceptions import MissingDependencyError, PdfToolError
from pdf_tool.router.file_inspector import FileInspector
from pdf_tool.router.registry import registry
from pdf_tool.utils.config import get_config
from pdf_tool.utils.dependency_checker import verify
from pdf_tool.utils.output_validator import validate_pdf
from pdf_tool.utils.progress import conversion_spinner

console = Console()
inspector = FileInspector()

_IMAGE_EXTS = {"jpeg", "jpg", "png", "webp", "tiff", "tif", "bmp", "gif", "heic", "heif"}
_DOC_EXTS = {
    "md",
    "markdown",
    "html",
    "htm",
    "docx",
    "doc",
    "odt",
    "rtf",
    "xlsx",
    "xls",
    "ods",
    "csv",
    "pptx",
    "ppt",
    "odp",
}

app = typer.Typer()


@dataclass
class BatchItemResult:
    input_file: Path
    output_file: Path | None
    target_fmt: str
    success: bool
    duration_seconds: float
    output_size_bytes: int = 0
    error_message: str | None = None
    engine: str = ""


def _expand_inputs(raw_inputs: list[Path]) -> list[Path]:
    """Expand wildcards/glob patterns in input arguments."""
    expanded: list[Path] = []
    for p in raw_inputs:
        p_str = str(p)
        if any(c in p_str for c in ("*", "?", "[")):
            matches = glob.glob(p_str, recursive=True)
            if matches:
                expanded.extend([Path(m) for m in sorted(matches)])
            else:
                expanded.append(p)
        else:
            expanded.append(p)
    return expanded


@app.command("convert")
def convert(
    input_files: Annotated[
        list[Path], typer.Argument(help="Input file(s) or glob pattern to convert.")
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Output file path (or target directory for batch conversions)."
        ),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Target directory for batch conversions."),
    ] = None,
    to: Annotated[
        str | None,
        typer.Option("--to", help="Target format (e.g. pdf, png, jpeg, docx, csv, txt)."),
    ] = None,
    batch: Annotated[
        bool,
        typer.Option(
            "--batch", "-b", help="Force batch mode (convert each input to a separate output)."
        ),
    ] = False,
    parallel: Annotated[
        bool,
        typer.Option("--parallel", "-j", help="Run batch conversions concurrently."),
    ] = False,
    workers: Annotated[
        int | None,
        typer.Option("--workers", "-w", help="Number of worker threads in parallel mode."),
    ] = None,
    dpi: Annotated[
        int | None,
        typer.Option("--dpi", help="DPI for image output. [default: from config or 150]"),
    ] = None,
    quality: Annotated[
        str | None,
        typer.Option(
            "--quality", help="Quality preset: high, medium, low. [default: from config or medium]"
        ),
    ] = None,
    pages: Annotated[
        str | None,
        typer.Option("--pages", help="Page range to extract (e.g. '1-3,5')."),
    ] = None,
    page: Annotated[
        int | None,
        typer.Option("--page", "-p", help="Specific page number (1-based) to extract from."),
    ] = None,
    table_index: Annotated[
        int | None,
        typer.Option("--table-index", help="Specific table index (1-based) to extract."),
    ] = None,
) -> None:
    """Convert file(s) between formats.

    For multiple image inputs targeting PDF without --batch, images are merged into a single PDF.
    Glob patterns like '*.docx' are supported for batch conversions.
    """
    if not input_files:
        console.print("[red]Error:[/red] No input files provided.")
        raise typer.Exit(1)

    config = get_config()
    actual_dpi = dpi if dpi is not None else int(config.get("defaults.image_dpi", 150))
    actual_quality = quality or config.get("defaults.quality", "medium")

    # Resolve output directory from config if not explicitly passed
    resolved_output_dir = output_dir
    if resolved_output_dir is None:
        cfg_out = config.get("defaults.output_dir", "")
        if cfg_out:
            resolved_output_dir = Path(cfg_out)

    # Check if output is a directory
    if output is not None and (output.is_dir() or str(output).endswith(("/", "\\"))):
        resolved_output_dir = output
        output = None

    # Expand glob patterns in input_files
    input_files = _expand_inputs(input_files)

    # Support positional syntax: pdf input.png output.pdf OR pdf img1.jpg img2.jpg out.pdf
    if (
        len(input_files) >= 2
        and output is None
        and not input_files[-1].exists()
        and input_files[-1].suffix
        and not any(c in str(input_files[-1]) for c in ("*", "?", "["))
    ):
        output = input_files[-1]
        input_files = input_files[:-1]

    # Validate all inputs exist
    for f in input_files:
        if not f.exists():
            console.print(f"[red]Error:[/red] File not found: '{f}'")
            raise typer.Exit(1)

    target_fmt = (to or "").lower().lstrip(".")
    if target_fmt == "jpg":
        target_fmt = "jpeg"

    # Multi-image → single PDF merge (when not in explicit batch mode)
    all_exts = {inspector.detect_extension(f) for f in input_files}
    is_multi_image_merge = (
        len(input_files) > 1
        and not batch
        and all_exts.issubset(_IMAGE_EXTS)
        and (target_fmt in ("pdf", "") or (output is not None and output.suffix.lower() == ".pdf"))
    )

    if is_multi_image_merge:
        out_path = output or (
            (resolved_output_dir / f"{input_files[0].stem}.pdf")
            if resolved_output_dir
            else input_files[0].with_suffix(".pdf")
        )
        adapter = ImageToPdfAdapter()
        extra = input_files[1:]

        with conversion_spinner(f"Merging {len(input_files)} images → PDF …"):
            try:
                result = adapter.convert(input_files[0], out_path, extra_inputs=extra)
            except PdfToolError as exc:
                console.print(f"[red]Error:[/red] {exc}")
                raise typer.Exit(1) from exc

        _print_summary(result)
        return

    # Check if this is a batch conversion (multiple files or explicit --batch)
    if len(input_files) > 1 or batch:
        _run_batch_conversion(
            input_files=input_files,
            target_dir=resolved_output_dir,
            target_fmt=target_fmt,
            parallel=parallel,
            workers=workers,
            options={
                "dpi": actual_dpi,
                "quality": actual_quality,
                "pages": pages,
                "page": page,
                "table_index": table_index,
            },
        )
        return

    # Single file conversion
    input_path = input_files[0]
    _, first_ext = inspector.detect(input_path)

    # Infer target format if not explicitly provided
    if not target_fmt:
        if output is not None and output.suffix:
            target_fmt = inspector.detect_extension(output)
        elif first_ext in _IMAGE_EXTS or first_ext in _DOC_EXTS:
            target_fmt = "pdf"
        elif first_ext == "pdf":
            target_fmt = "png"
        else:
            console.print(
                "[red]Error:[/red] Please specify target format via --to <format> or an output path."
            )
            raise typer.Exit(1)

    if target_fmt == "jpg":
        target_fmt = "jpeg"

    try:
        adapter_cls = registry.lookup(first_ext, target_fmt)
    except PdfToolError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    adapter = adapter_cls()

    # Check system dependencies
    if adapter.required_system_deps:
        try:
            verify(adapter.required_system_deps)
        except MissingDependencyError as exc:
            console.print(f"[red]Missing dependency:[/red] {exc}")
            if exc.install_hints:
                console.print("[yellow]Install commands for your system:[/yellow]")
                for os_name, cmd in exc.install_hints.items():
                    console.print(f"  • {os_name}: [cyan]{cmd}[/cyan]")
            raise typer.Exit(1) from exc
        except PdfToolError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    out_ext = _resolve_out_ext(target_fmt)
    if output:
        out_path = output
    elif resolved_output_dir:
        resolved_output_dir.mkdir(parents=True, exist_ok=True)
        out_path = resolved_output_dir / f"{input_path.stem}{out_ext}"
    else:
        out_path = input_path.with_suffix(out_ext)

    options: dict = {
        "dpi": actual_dpi,
        "quality": actual_quality,
        "pages": pages,
        "page": page,
        "table_index": table_index,
    }

    with conversion_spinner(f"Converting '{input_path.name}' → {target_fmt.upper()} …"):
        try:
            result = adapter.convert(input_path, out_path, **options)
        except PdfToolError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    # Validate output for PDFs
    if target_fmt == "pdf":
        try:
            validate_pdf(result.output_path)
        except PdfToolError as exc:
            console.print(f"[red]Validation failed:[/red] {exc}")
            raise typer.Exit(1) from exc

    _print_summary(result)


def _convert_single_item(
    input_path: Path,
    target_dir: Path | None,
    target_fmt: str | None,
    options: dict,
) -> BatchItemResult:
    """Worker function to convert a single file in batch mode."""
    start_time = time.perf_counter()
    try:
        if not input_path.exists():
            return BatchItemResult(
                input_file=input_path,
                output_file=None,
                target_fmt=target_fmt or "unknown",
                success=False,
                duration_seconds=time.perf_counter() - start_time,
                error_message="File not found",
            )

        _, in_ext = inspector.detect(input_path)
        actual_fmt = (target_fmt or "").lower().lstrip(".")
        if not actual_fmt:
            if in_ext in _IMAGE_EXTS or in_ext in _DOC_EXTS:
                actual_fmt = "pdf"
            elif in_ext == "pdf":
                actual_fmt = "png"
            else:
                return BatchItemResult(
                    input_file=input_path,
                    output_file=None,
                    target_fmt="unknown",
                    success=False,
                    duration_seconds=time.perf_counter() - start_time,
                    error_message=f"Cannot determine target format for '{in_ext}'",
                )

        if actual_fmt == "jpg":
            actual_fmt = "jpeg"

        adapter_cls = registry.lookup(in_ext, actual_fmt)
        adapter = adapter_cls()

        if adapter.required_system_deps:
            verify(adapter.required_system_deps)

        out_ext = _resolve_out_ext(actual_fmt)
        if target_dir:
            target_dir.mkdir(parents=True, exist_ok=True)
            out_path = target_dir / f"{input_path.stem}{out_ext}"
        else:
            out_path = input_path.with_suffix(out_ext)

        result = adapter.convert(input_path, out_path, **options)
        if actual_fmt == "pdf":
            validate_pdf(result.output_path)

        return BatchItemResult(
            input_file=input_path,
            output_file=result.output_path,
            target_fmt=actual_fmt,
            success=True,
            duration_seconds=result.duration_seconds,
            output_size_bytes=result.output_size_bytes,
            engine=result.engine,
        )
    except Exception as exc:
        return BatchItemResult(
            input_file=input_path,
            output_file=None,
            target_fmt=target_fmt or "unknown",
            success=False,
            duration_seconds=time.perf_counter() - start_time,
            error_message=str(exc),
        )


def _run_batch_conversion(
    input_files: list[Path],
    target_dir: Path | None,
    target_fmt: str | None,
    parallel: bool,
    workers: int | None,
    options: dict,
) -> None:
    """Execute batch conversions either sequentially or in parallel."""
    total_files = len(input_files)
    batch_start = time.perf_counter()
    results: list[BatchItemResult] = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("• {task.completed}/{task.total} files"),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task_id = progress.add_task(
            f"Converting {total_files} file(s)" + (" (parallel)" if parallel else "") + " …",
            total=total_files,
        )

        if parallel:
            max_workers = workers or min(32, total_files)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(
                        _convert_single_item,
                        file,
                        target_dir,
                        target_fmt,
                        options,
                    ): file
                    for file in input_files
                }
                for future in concurrent.futures.as_completed(future_to_file):
                    res = future.result()
                    results.append(res)
                    progress.advance(task_id)
        else:
            for file in input_files:
                res = _convert_single_item(file, target_dir, target_fmt, options)
                results.append(res)
                progress.advance(task_id)

    total_duration = time.perf_counter() - batch_start

    # Preserve input ordering in results
    input_order = {p: i for i, p in enumerate(input_files)}
    results.sort(key=lambda r: input_order.get(r.input_file, 0))

    _print_batch_summary(results, total_duration)

    failed_count = sum(1 for r in results if not r.success)
    if failed_count > 0:
        raise typer.Exit(1)


def _resolve_out_ext(target_fmt: str) -> str:
    ext_map = {
        "jpeg": ".jpg",
        "png": ".png",
        "pdf": ".pdf",
        "docx": ".docx",
        "csv": ".csv",
        "xlsx": ".xlsx",
        "md": ".md",
        "markdown": ".md",
        "txt": ".txt",
    }
    return ext_map.get(target_fmt, f".{target_fmt}")


def _print_summary(result) -> None:
    """Print a Rich summary table for a completed conversion."""
    table = Table(title="✅ Conversion Complete", show_header=True, header_style="bold green")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Output", str(result.output_path))
    table.add_row("Engine", result.engine)
    table.add_row("Input size", _fmt_bytes(result.input_size_bytes))
    table.add_row("Output size", _fmt_bytes(result.output_size_bytes))
    table.add_row("Duration", f"{result.duration_seconds:.2f}s")
    console.print(table)


def _print_batch_summary(results: list[BatchItemResult], total_time: float) -> None:
    """Print a Rich summary table for a completed batch conversion."""
    table = Table(title="📦 Batch Conversion Summary", show_header=True, header_style="bold cyan")
    table.add_column("Input File", style="bold")
    table.add_column("Target", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Details")

    succeeded = 0
    failed = 0
    for r in results:
        if r.success:
            succeeded += 1
            status_str = "[green]✅ Success[/green]"
            details = (
                f"{r.output_file.name} ({_fmt_bytes(r.output_size_bytes)})"
                if r.output_file
                else "OK"
            )
        else:
            failed += 1
            status_str = "[red]❌ Failed[/red]"
            details = f"[red]{r.error_message}[/red]"

        table.add_row(
            r.input_file.name,
            r.target_fmt.upper(),
            status_str,
            f"{r.duration_seconds:.2f}s",
            details,
        )

    console.print()
    console.print(table)
    summary_color = "green" if failed == 0 else ("yellow" if succeeded > 0 else "red")
    console.print(
        f"[{summary_color}]Total files: {len(results)}  |  "
        f"Succeeded: {succeeded}  |  "
        f"Failed: {failed}  |  "
        f"Total time: {total_time:.2f}s[/{summary_color}]\n"
    )


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
