"""pdf-tool CLI — doctor command (dependency diagnostic)."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from pdf_tool import __version__
from pdf_tool.utils.dependency_checker import check_all

console = Console()
app = typer.Typer()

_DEPS_TO_CHECK = [
    (
        "gs",
        "Ghostscript",
        "PDF Compress",
        "sudo pacman -S ghostscript / sudo apt install ghostscript / brew install ghostscript",
    ),
    (
        "soffice",
        "LibreOffice",
        "DOCX/PPTX/XLSX → PDF",
        "sudo pacman -S libreoffice-fresh / sudo apt install libreoffice / brew install libreoffice",
    ),
    (
        "tesseract",
        "Tesseract",
        "OCR",
        "sudo pacman -S tesseract / sudo apt install tesseract-ocr / brew install tesseract",
    ),
    (
        "mmdc",
        "Mermaid CLI",
        "Markdown Mermaid diagrams & flowcharts → PDF",
        "npm install -g @mermaid-js/mermaid-cli",
    ),
]

_PURE_PYTHON_ADAPTERS = [
    ("Pillow", "Image → PDF (JPG, PNG, WEBP, TIFF, HEIC)", "Built-in Python library"),
    ("PyMuPDF", "PDF → Image, PDF validation", "Built-in Python library"),
    (
        "WeasyPrint",
        "Markdown (.md) & HTML → PDF (with CSS & syntax highlight)",
        "Built-in Python library",
    ),
    ("pdf2docx", "PDF → Word (.docx) layout reconstruction", "Built-in Python library"),
    ("pdfplumber", "PDF → CSV & Excel table extraction", "Built-in Python library"),
    ("pymupdf4llm", "PDF → Structured Markdown & plain text", "Built-in Python library"),
    ("pypdf", "Merge, Split", "Built-in Python library"),
]


@app.command("doctor")
def doctor() -> None:
    """Check system dependencies and print a diagnostic table."""
    console.print(f"\n[bold]pdf-tool[/bold] v{__version__}  |  Python {sys.version.split()[0]}\n")

    # System dependency table
    sys_table = Table(
        title="🩺 System Dependencies",
        show_header=True,
        header_style="bold cyan",
    )
    sys_table.add_column("Adapter / Tool", style="bold")
    sys_table.add_column("Binary")
    sys_table.add_column("Status")
    sys_table.add_column("Install Command")

    statuses = check_all([dep[0] for dep in _DEPS_TO_CHECK])
    for (binary, name, usage, install_cmd), status in zip(_DEPS_TO_CHECK, statuses):
        if status.found:
            status_str = f"[green]✅ Found[/green]  {status.path}"
        else:
            status_str = "[red]❌ Not found[/red]"
        sys_table.add_row(f"{name} ({usage})", binary, status_str, install_cmd)

    console.print(sys_table)

    # Pure-Python adapter table
    py_table = Table(
        title="🐍 Pure-Python Adapters (no system deps required)",
        show_header=True,
        header_style="bold cyan",
    )
    py_table.add_column("Adapter", style="bold")
    py_table.add_column("Supports")
    py_table.add_column("Status")

    for name, supports, _ in _PURE_PYTHON_ADAPTERS:
        py_table.add_row(name, supports, "[green]✅ Built-in[/green]")

    console.print(py_table)
    console.print()
