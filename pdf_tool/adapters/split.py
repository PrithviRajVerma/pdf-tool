"""PDF split adapter using pypdf."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError


def _parse_page_range(spec: str, max_page: int) -> list[int]:
    """Parse a page range spec like ``"1-3,5,7-9"`` into 0-based indices.

    Args:
        spec: Page range (1-based, inclusive).
        max_page: Total number of pages.

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


class SplitAdapter(BaseAdapter):
    """Split a PDF by page range or into equal-sized chunks using pypdf."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "pypdf"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Not used directly — call :meth:`split` instead."""
        raise NotImplementedError("Use SplitAdapter.split() directly.")

    def split(
        self,
        input_path: Path,
        output_dir: Path,
        page_range: str | None = None,
        every: int | None = None,
    ) -> list[Path]:
        """Split *input_path* into one or more output PDFs.

        If *page_range* is given, extract those pages into a **single** output PDF
        named ``<stem>_pages_<spec>.pdf``.

        If *every* is given, split into chunks of *every* pages each, named
        ``<stem>_part_001.pdf``, ``<stem>_part_002.pdf``, etc.

        If neither is given, every page becomes its own PDF.

        Args:
            input_path: Source PDF path.
            output_dir: Directory where output PDFs are written.
            page_range: Page range spec, e.g. ``"1-3,5"``.
            every: Chunk size (pages per output file).

        Returns:
            List of generated output :class:`Path` objects.

        Raises:
            InvalidInputError: If the PDF cannot be opened.
            ConversionFailedError: If writing any output file fails.
        """
        try:
            reader = PdfReader(str(input_path))
        except Exception as exc:
            raise InvalidInputError(f"Cannot open PDF '{input_path}': {exc}") from exc

        total = len(reader.pages)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = input_path.stem
        outputs: list[Path] = []

        if page_range is not None:
            indices = _parse_page_range(page_range, total)
            writer = PdfWriter()
            for idx in indices:
                writer.add_page(reader.pages[idx])
            safe_spec = page_range.replace(",", "-").replace(" ", "")
            out = output_dir / f"{stem}_pages_{safe_spec}.pdf"
            try:
                with out.open("wb") as fh:
                    writer.write(fh)
            except Exception as exc:
                raise ConversionFailedError(f"Failed to write '{out}': {exc}") from exc
            outputs.append(out)

        elif every is not None:
            chunk_size = max(1, every)
            for chunk_num, chunk_start in enumerate(range(0, total, chunk_size), start=1):
                writer = PdfWriter()
                for idx in range(chunk_start, min(chunk_start + chunk_size, total)):
                    writer.add_page(reader.pages[idx])
                out = output_dir / f"{stem}_part_{chunk_num:03d}.pdf"
                try:
                    with out.open("wb") as fh:
                        writer.write(fh)
                except Exception as exc:
                    raise ConversionFailedError(f"Failed to write '{out}': {exc}") from exc
                outputs.append(out)

        else:
            # One page per file
            for page_idx in range(total):
                writer = PdfWriter()
                writer.add_page(reader.pages[page_idx])
                out = output_dir / f"{stem}_page_{page_idx + 1:03d}.pdf"
                try:
                    with out.open("wb") as fh:
                        writer.write(fh)
                except Exception as exc:
                    raise ConversionFailedError(f"Failed to write '{out}': {exc}") from exc
                outputs.append(out)

        return outputs
