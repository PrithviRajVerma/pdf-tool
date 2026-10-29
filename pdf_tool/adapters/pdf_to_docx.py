"""PDF to DOCX (Microsoft Word) adapter using pdf2docx."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pymupdf as fitz
from pdf2docx import Converter
from rich.console import Console

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.adapters.pdf_to_image import _parse_page_range
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry

console = Console()


@registry.register(input_fmts=["pdf"], output_fmt="docx")
class PdfToDocxAdapter(BaseAdapter):
    """Converts PDF documents into editable Word (.docx) documents."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "pdf2docx"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert PDF to Word DOCX.

        Args:
            input_path: Source PDF path.
            output_path: Target DOCX path.
            **options:
                pages (str | None): Optional page range spec (e.g. "1-3,5").

        Returns:
            ConversionResult with metadata.

        Raises:
            InvalidInputError: If the PDF cannot be opened.
            ConversionFailedError: If the conversion process fails.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"File not found: '{input_path}'")

        # Verify PDF and check if it has extractable text
        try:
            doc = fitz.open(str(input_path))
            total_pages = doc.page_count
            if total_pages == 0:
                doc.close()
                raise InvalidInputError(f"PDF '{input_path.name}' has no pages.")

            # Quick check for selectable text
            has_text = any(len(page.get_text().strip()) > 0 for page in doc)
            doc.close()

            if not has_text:
                console.print(
                    "[yellow]Note:[/yellow] PDF appears to be scanned or contains no selectable text. "
                    "The generated DOCX will contain embedded images. For editable text, run 'pdf ocr' first."
                )
        except Exception as exc:
            if isinstance(exc, InvalidInputError):
                raise
            raise InvalidInputError(f"Cannot open PDF '{input_path}': {exc}") from exc

        page_spec = options.get("pages")
        page_indices = _parse_page_range(page_spec, total_pages) if page_spec else None

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Silence excessive internal pdf2docx logging
        logging.getLogger("pdf2docx").setLevel(logging.WARNING)

        cv = None
        try:
            cv = Converter(str(input_path))
            cv.convert(str(output_path), pages=page_indices)
        except Exception as exc:
            raise ConversionFailedError(f"Failed to convert PDF to DOCX: {exc}") from exc
        finally:
            if cv is not None:
                try:
                    cv.close()
                except Exception:
                    pass

        return self._make_result(input_path, output_path, start)
