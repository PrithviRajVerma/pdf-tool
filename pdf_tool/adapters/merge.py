"""PDF merge adapter using pypdf."""

from __future__ import annotations

import time
from pathlib import Path

from pypdf import PdfWriter

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry


@registry.register(input_fmts=["pdf"], output_fmt="pdf")
class MergeAdapter(BaseAdapter):
    """Merge multiple PDF files into a single PDF using pypdf.

    This adapter is registered for ``pdf → pdf`` conversion.
    For multi-file merging, use :meth:`merge` directly.
    """

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "pypdf"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Pass-through single-file convert (delegates to merge with one file).

        Use :meth:`merge` for multi-file merging.
        """
        return self.merge([input_path], output_path)

    def merge(self, input_paths: list[Path], output_path: Path) -> ConversionResult:
        """Merge all PDFs in *input_paths* (in order) into *output_path*.

        Args:
            input_paths: Ordered list of PDF files to merge.
            output_path: Destination merged PDF path.

        Returns:
            :class:`ConversionResult` metadata.

        Raises:
            InvalidInputError: If any input PDF cannot be opened.
            ConversionFailedError: If writing the merged PDF fails.
        """
        if not input_paths:
            raise InvalidInputError("Cannot merge an empty list of files.")

        start = time.monotonic()

        writer = PdfWriter()
        total_input_bytes = 0

        for path in input_paths:
            if not path.exists():
                raise InvalidInputError(f"Input file not found: '{path}'")
            total_input_bytes += path.stat().st_size
            try:
                writer.append(str(path))
            except Exception as exc:
                raise InvalidInputError(f"Cannot read PDF '{path}': {exc}") from exc

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output_path.open("wb") as fh:
                writer.write(fh)
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to write merged PDF '{output_path}': {exc}"
            ) from exc

        first_input = input_paths[0] if input_paths else output_path
        return ConversionResult(
            input_path=first_input,
            output_path=output_path,
            input_size_bytes=total_input_bytes,
            output_size_bytes=output_path.stat().st_size if output_path.exists() else 0,
            duration_seconds=time.monotonic() - start,
            engine=self.engine_name,
        )
