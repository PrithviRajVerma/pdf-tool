"""PDF to structured Markdown and plain text adapter using PyMuPDF and pymupdf4llm."""

from __future__ import annotations

import time
from pathlib import Path

import pymupdf as fitz
import pymupdf4llm

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.adapters.pdf_to_image import _parse_page_range
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry


@registry.register(input_fmts=["pdf"], output_fmt="md")
@registry.register(input_fmts=["pdf"], output_fmt="markdown")
@registry.register(input_fmts=["pdf"], output_fmt="txt")
class PdfToTextAdapter(BaseAdapter):
    """Converts PDF documents into structured Markdown (.md) or plain text (.txt)."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "pymupdf4llm"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert PDF to Markdown or plain text.

        Args:
            input_path: Source PDF path.
            output_path: Target .md or .txt path.
            **options:
                pages (str | None): Optional page range spec (e.g. "1-3,5").

        Returns:
            ConversionResult with metadata.

        Raises:
            InvalidInputError: If the PDF cannot be opened.
            ConversionFailedError: If extraction fails.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"File not found: '{input_path}'")

        try:
            doc = fitz.open(str(input_path))
            total_pages = doc.page_count
            if total_pages == 0:
                doc.close()
                raise InvalidInputError(f"PDF '{input_path.name}' has no pages.")
        except Exception as exc:
            if isinstance(exc, InvalidInputError):
                raise
            raise InvalidInputError(f"Cannot open PDF '{input_path}': {exc}") from exc

        page_spec = options.get("pages")
        page_indices = _parse_page_range(page_spec, total_pages) if page_spec else None

        output_path.parent.mkdir(parents=True, exist_ok=True)
        is_txt = output_path.suffix.lower() == ".txt"

        try:
            if is_txt:
                pages_to_read = (
                    page_indices if page_indices is not None else list(range(total_pages))
                )
                parts = []
                for idx in pages_to_read:
                    page_text = doc[idx].get_text("text")
                    parts.append(page_text)
                extracted_content = "\n\n--- Page Break ---\n\n".join(parts)
            else:
                extracted_content = pymupdf4llm.to_markdown(
                    str(input_path),
                    pages=page_indices,
                )

            output_path.write_text(extracted_content, encoding="utf-8")
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to extract text from '{input_path.name}': {exc}"
            ) from exc
        finally:
            doc.close()

        return self._make_result(input_path, output_path, start)
