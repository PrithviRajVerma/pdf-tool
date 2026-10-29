"""PDF compression adapter — Ghostscript primary, pypdf fallback."""

from __future__ import annotations

import shutil
import subprocess
import time
import warnings
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError

# Ghostscript PDF settings map
_GS_SETTINGS = {
    "high": "/screen",
    "medium": "/ebook",
    "low": "/printer",
}


class CompressAdapter(BaseAdapter):
    """Compress a PDF using Ghostscript (primary) or pypdf (fallback).

    Ghostscript provides much stronger compression. pypdf's
    ``compress_content_streams()`` is used as a zero-system-dep fallback.
    """

    @property
    def required_system_deps(self) -> list[str]:
        return ["gs"]  # Ghostscript

    @property
    def engine_name(self) -> str:
        return "Ghostscript"

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        level: str = "medium",
    ) -> ConversionResult:
        """Compress *input_path* and write to *output_path*.

        Args:
            input_path: Source PDF path.
            output_path: Destination compressed PDF path.
            level: Compression level — ``"high"``, ``"medium"``, or ``"low"``.

        Returns:
            :class:`ConversionResult` metadata.

        Raises:
            InvalidInputError: If the source PDF cannot be read.
            ConversionFailedError: If compression fails.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"Input file not found: '{input_path}'")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_setting = _GS_SETTINGS.get(level.lower(), "/ebook")

        gs_path = shutil.which("gs")
        if gs_path:
            self._compress_gs(gs_path, input_path, output_path, pdf_setting)
        else:
            warnings.warn(
                "Ghostscript ('gs') not found in PATH. "
                "Falling back to pypdf compression (less aggressive).",
                UserWarning,
                stacklevel=2,
            )
            self._compress_pypdf(input_path, output_path)

        return ConversionResult(
            input_path=input_path,
            output_path=output_path,
            input_size_bytes=input_path.stat().st_size,
            output_size_bytes=output_path.stat().st_size if output_path.exists() else 0,
            duration_seconds=time.monotonic() - start,
            engine="Ghostscript" if gs_path else "pypdf",
        )

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Delegate to :meth:`compress`."""
        level = options.get("level", "medium")
        return self.compress(input_path, output_path, level=level)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compress_gs(
        self,
        gs_bin: str,
        input_path: Path,
        output_path: Path,
        pdf_setting: str,
    ) -> None:
        cmd = [
            gs_bin,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={pdf_setting}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output_path}",
            str(input_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConversionFailedError(
                f"Ghostscript failed (exit {result.returncode}): {result.stderr}"
            )

    def _compress_pypdf(self, input_path: Path, output_path: Path) -> None:
        try:
            reader = PdfReader(str(input_path))
        except Exception as exc:
            raise InvalidInputError(f"Cannot read PDF '{input_path}': {exc}") from exc

        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)

        try:
            with output_path.open("wb") as fh:
                writer.write(fh)
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to write compressed PDF '{output_path}': {exc}"
            ) from exc
