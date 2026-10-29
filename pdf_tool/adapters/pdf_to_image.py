"""PDF → Image adapter using PyMuPDF (fitz)."""

from __future__ import annotations

import time
from pathlib import Path

import pymupdf as fitz

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry


def _parse_page_range(spec: str, max_page: int) -> list[int]:
    """Parse a page range string like ``"1-3,5,7-9"`` into 0-based indices.

    Args:
        spec: Page range specification (1-based, inclusive).
        max_page: Total number of pages in the document.

    Returns:
        Sorted list of unique 0-based page indices.
    """
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = int(start_s.strip()) - 1
            end = int(end_s.strip()) - 1
            for i in range(start, end + 1):
                if 0 <= i < max_page:
                    pages.add(i)
        else:
            idx = int(part) - 1
            if 0 <= idx < max_page:
                pages.add(idx)
    return sorted(pages)


@registry.register(input_fmts=["pdf"], output_fmt="jpeg")
@registry.register(input_fmts=["pdf"], output_fmt="jpg")
@registry.register(input_fmts=["pdf"], output_fmt="png")
class PdfToImageAdapter(BaseAdapter):
    """Convert PDF pages to raster images using PyMuPDF."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "PyMuPDF"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert PDF pages to image files.

        Args:
            input_path: Source PDF.
            output_path: Target image path. For multi-page output the stem
                is suffixed with ``_p1``, ``_p2``, etc.
            **options:
                dpi (int): Resolution in DPI (default: 150).
                pages (str | None): Page range spec, e.g. ``"1-3,5"`` (default: all).

        Returns:
            :class:`ConversionResult` — ``output_path`` points to the first
            (or only) generated image.

        Raises:
            InvalidInputError: If the PDF cannot be opened.
            ConversionFailedError: If rendering fails.
        """
        start = time.monotonic()
        dpi: int = int(options.get("dpi", 150))
        page_spec: str | None = options.get("pages", None)

        try:
            doc = fitz.open(str(input_path))
        except Exception as exc:
            raise InvalidInputError(f"Cannot open PDF '{input_path}': {exc}") from exc

        total_pages = doc.page_count
        if total_pages == 0:
            doc.close()
            raise InvalidInputError(f"PDF '{input_path}' has no pages.")

        page_indices = (
            _parse_page_range(page_spec, total_pages) if page_spec else list(range(total_pages))
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ext = output_path.suffix.lstrip(".").lower()
        fitz_ext = "jpg" if ext in ("jpg", "jpeg") else "png"
        if not output_path.suffix:
            output_path = output_path.with_suffix(f".{fitz_ext}")

        generated: list[Path] = []
        try:
            for local_idx, page_idx in enumerate(page_indices):
                page = doc[page_idx]
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat, alpha=False)

                if len(page_indices) == 1:
                    dest = output_path
                else:
                    dest = output_path.with_name(f"{output_path.stem}_p{local_idx + 1}.{fitz_ext}")

                pix.save(str(dest))
                generated.append(dest)
        except Exception as exc:
            doc.close()
            raise ConversionFailedError(
                f"Failed to render page from '{input_path}': {exc}"
            ) from exc

        doc.close()

        first_out = generated[0] if generated else output_path
        total_output_bytes = sum(p.stat().st_size for p in generated if p.exists())
        return ConversionResult(
            input_path=input_path,
            output_path=first_out,
            input_size_bytes=input_path.stat().st_size,
            output_size_bytes=total_output_bytes,
            duration_seconds=time.monotonic() - start,
            engine=self.engine_name,
        )
