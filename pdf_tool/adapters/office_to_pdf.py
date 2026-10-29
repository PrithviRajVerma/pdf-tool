"""Office document to PDF conversion adapter using headless LibreOffice."""

from __future__ import annotations

import time
from pathlib import Path

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.router.registry import registry
from pdf_tool.utils.libreoffice import run_libreoffice_convert

_OFFICE_FORMATS = [
    # Word documents
    "docx",
    "doc",
    "odt",
    "rtf",
    # Spreadsheets
    "xlsx",
    "xls",
    "ods",
    "csv",
    # Presentations
    "pptx",
    "ppt",
    "odp",
]


@registry.register(input_fmts=_OFFICE_FORMATS, output_fmt="pdf")
class OfficeToPdfAdapter(BaseAdapter):
    """Converts Microsoft Office and OpenDocument files to PDF using LibreOffice."""

    @property
    def required_system_deps(self) -> list[str]:
        return ["soffice"]

    @property
    def engine_name(self) -> str:
        return "LibreOffice"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert office document to PDF.

        Args:
            input_path: Source document path.
            output_path: Target PDF path.
            **options:
                timeout (float): Max conversion time in seconds (default: 60.0).

        Returns:
            ConversionResult with metadata.
        """
        start = time.monotonic()
        timeout = float(options.get("timeout", 60.0))

        run_libreoffice_convert(input_path, output_path, timeout=timeout)

        return self._make_result(input_path, output_path, start)
