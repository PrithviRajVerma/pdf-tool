"""pdf-tool CLI — compress command (multi-format: PDF, Images, Office documents)."""

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

from pdf_tool.adapters.compress import CompressAdapter
from pdf_tool.exceptions import PdfToolError
from pdf_tool.utils.config import get_config
from pdf_tool.utils.output_validator import validate_pdf
from pdf_tool.utils.progress import conversion_spinner
from pdf_tool.utils.size_parser import parse_size_bytes

console = Console()
app = typer.Typer()

_VALID_LEVELS = {"high", "medium", "low"}


@dataclass
class CompressItemResult:
    input_file: Path
    output_file: Path | None
    success: bool
    input_size_bytes: int
    output_size_bytes: int
    duration_seconds: float
    engine: str = ""
    error_message: str | None = None


def _expand_inputs(raw_inputs: list[Path]) -> list[Path]:
    """Expand wildcards/glob patterns in input arguments."""
    expanded: list[Path] = []
    for p in raw_inputs:
        p_str = str(p)
        if any(c in p_str for c in ("*", "?", "[")):
            matches = glob.glob(p_str, recursive=True)
            if matches:
                expanded.extend(sorted(Path(m) for m in matches if Path(m).is_file()))
            else:
                expanded.append(p)
        else:
            expanded.append(p)
    return expanded


@app.command("compress")
def compress(
    files: Annotated[
        list[Path],
        typer.Argument(help="File(s) or glob pattern to compress (PDF, Image, DOCX, PPTX, XLSX)."),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output compressed file path (or target directory)."),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", help="Target directory for batch compression."),
    ] = None,
    level: Annotated[
        str | None,
        typer.Option(
            "--level", help="Compression level: high, medium, low. [default: from config or medium]"
        ),
    ] = None,
    max_dim: Annotated[
        int | None,
        typer.Option("--max-dim", help="Max image pixel dimension (e.g. 1920)."),
    ] = None,
    target_size: Annotated[
        str | None,
        typer.Option("--target-size", help="Target maximum file size (e.g. '2MB', '500KB')."),
    ] = None,
    to_webp: Annotated[
        bool,
        typer.Option("--to-webp", help="Convert compressed images to WebP format."),
    ] = False,
    parallel: Annotated[
        bool,
        typer.Option("--parallel", "-j", help="Run batch compression concurrently."),
    ] = False,
    workers: Annotated[
        int | None,
        typer.Option("--workers", "-w", help="Number of worker threads in parallel mode."),
    ] = None,
) -> None:
    """Compress PDF, image, or office files to reduce file size."""
    config = get_config()
    actual_level = (level or config.get("defaults.compression_level", "medium")).lower()

    if actual_level not in _VALID_LEVELS:
        console.print(
            f"[red]Error:[/red] Invalid level '{actual_level}'. Choose: high, medium, low."
        )
        raise typer.Exit(1)

    target_size_bytes: int | None = None
    if target_size:
        try:
            target_size_bytes = parse_size_bytes(target_size)
        except ValueError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    resolved_inputs = _expand_inputs(files)

    # If single file
    if len(resolved_inputs) == 1:
        input_file = resolved_inputs[0]
        if not input_file.exists():
            console.print(f"[red]Error:[/red] File not found: '{input_file}'")
            raise typer.Exit(1)

        out_ext = (
            ".webp" if (to_webp and input_file.suffix.lower() != ".pdf") else input_file.suffix
        )
        if output:
            if output.is_dir() or output_dir:
                dest_dir = output_dir or output
                dest_dir.mkdir(parents=True, exist_ok=True)
                out_path = dest_dir / f"{input_file.stem}_compressed{out_ext}"
            else:
                out_path = output
        elif output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_path = output_dir / f"{input_file.stem}_compressed{out_ext}"
        else:
            out_path = input_file.with_stem(input_file.stem + "_compressed").with_suffix(out_ext)

        adapter = CompressAdapter()
        with conversion_spinner(f"Compressing '{input_file.name}' (level={actual_level}) …"):
            try:
                result = adapter.compress(
                    input_file,
                    out_path,
                    level=actual_level,
                    max_dim=max_dim,
                    target_size_bytes=target_size_bytes,
                )
            except PdfToolError as exc:
                console.print(f"[red]Error:[/red] {exc}")
                raise typer.Exit(1) from exc

        if result.output_path.suffix.lower() == ".pdf":
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
        return

    # Batch compression
    dest_dir = output_dir or (output if (output and output.is_dir()) else Path("."))
    dest_dir.mkdir(parents=True, exist_ok=True)

    _run_batch_compression(
        input_files=resolved_inputs,
        target_dir=dest_dir,
        level=actual_level,
        max_dim=max_dim,
        target_size_bytes=target_size_bytes,
        to_webp=to_webp,
        parallel=parallel,
        workers=workers,
    )


def _compress_single_item(
    input_path: Path,
    target_dir: Path,
    level: str,
    max_dim: int | None,
    target_size_bytes: int | None,
    to_webp: bool,
) -> CompressItemResult:
    start_time = time.perf_counter()
    if not input_path.exists():
        return CompressItemResult(
            input_file=input_path,
            output_file=None,
            success=False,
            input_size_bytes=0,
            output_size_bytes=0,
            duration_seconds=time.perf_counter() - start_time,
            error_message="File not found",
        )

    out_ext = ".webp" if (to_webp and input_path.suffix.lower() != ".pdf") else input_path.suffix
    out_path = target_dir / f"{input_path.stem}_compressed{out_ext}"
    adapter = CompressAdapter()
    try:
        res = adapter.compress(
            input_path,
            out_path,
            level=level,
            max_dim=max_dim,
            target_size_bytes=target_size_bytes,
        )
        if out_path.suffix.lower() == ".pdf":
            validate_pdf(res.output_path)
        return CompressItemResult(
            input_file=input_path,
            output_file=res.output_path,
            success=True,
            input_size_bytes=res.input_size_bytes,
            output_size_bytes=res.output_size_bytes,
            duration_seconds=res.duration_seconds,
            engine=res.engine,
        )
    except Exception as exc:
        return CompressItemResult(
            input_file=input_path,
            output_file=None,
            success=False,
            input_size_bytes=input_path.stat().st_size if input_path.exists() else 0,
            output_size_bytes=0,
            duration_seconds=time.perf_counter() - start_time,
            error_message=str(exc),
        )


def _run_batch_compression(
    input_files: list[Path],
    target_dir: Path,
    level: str,
    max_dim: int | None,
    target_size_bytes: int | None,
    to_webp: bool,
    parallel: bool,
    workers: int | None,
) -> None:
    total_files = len(input_files)
    batch_start = time.perf_counter()
    results: list[CompressItemResult] = []

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
            f"Compressing {total_files} file(s)" + (" (parallel)" if parallel else "") + " …",
            total=total_files,
        )

        if parallel:
            max_workers = workers or min(16, total_files)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(
                        _compress_single_item,
                        f,
                        target_dir,
                        level,
                        max_dim,
                        target_size_bytes,
                        to_webp,
                    ): f
                    for f in input_files
                }
                for future in concurrent.futures.as_completed(future_to_file):
                    res = future.result()
                    results.append(res)
                    progress.advance(task_id)
        else:
            for f in input_files:
                res = _compress_single_item(
                    f, target_dir, level, max_dim, target_size_bytes, to_webp
                )
                results.append(res)
                progress.advance(task_id)

    total_duration = time.perf_counter() - batch_start
    # Preserve original file order
    results_map = {r.input_file: r for r in results}
    ordered_results = [results_map[f] for f in input_files if f in results_map]

    _print_batch_compress_summary(ordered_results, total_duration)

    failed_count = sum(1 for r in ordered_results if not r.success)
    if failed_count > 0:
        raise typer.Exit(1)


def _print_batch_compress_summary(results: list[CompressItemResult], total_time: float) -> None:
    table = Table(title="📦 Batch Compression Summary", show_header=True, header_style="bold cyan")
    table.add_column("Input File", style="bold")
    table.add_column("Status")
    table.add_column("Original")
    table.add_column("Compressed")
    table.add_column("Saved")
    table.add_column("Duration")

    succeeded = 0
    total_in = 0
    total_out = 0

    for r in results:
        if r.success:
            succeeded += 1
            total_in += r.input_size_bytes
            total_out += r.output_size_bytes
            delta = r.input_size_bytes - r.output_size_bytes
            pct = (delta / r.input_size_bytes * 100) if r.input_size_bytes else 0
            status_str = "[green]✅ Success[/green]"
            table.add_row(
                r.input_file.name,
                status_str,
                _fmt_bytes(r.input_size_bytes),
                _fmt_bytes(r.output_size_bytes),
                f"{pct:.1f}% ({_fmt_bytes(delta)})",
                f"{r.duration_seconds:.2f}s",
            )
        else:
            status_str = "[red]❌ Failed[/red]"
            table.add_row(
                r.input_file.name,
                status_str,
                _fmt_bytes(r.input_size_bytes),
                "-",
                f"[red]{r.error_message}[/red]",
                f"{r.duration_seconds:.2f}s",
            )

    console.print(table)
    total_saved = total_in - total_out
    total_pct = (total_saved / total_in * 100) if total_in else 0
    console.print(
        f"[bold]Total:[/bold] {succeeded}/{len(results)} files compressed in {total_time:.2f}s  |  "
        f"Saved [bold green]{_fmt_bytes(total_saved)}[/bold green] ({total_pct:.1f}% overall)"
    )


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
