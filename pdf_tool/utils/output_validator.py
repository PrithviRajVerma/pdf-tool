"""Output file validators for post-conversion integrity checks."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from pdf_tool.exceptions import OutputValidationError


def validate_pdf(path: Path) -> None:
    """Verify that *path* is a readable, non-empty PDF file.

    Args:
        path: Path to the PDF file to validate.

    Raises:
        OutputValidationError: If the file cannot be opened or has no pages.
    """
    validate_exists(path)
    try:
        doc = fitz.open(str(path))
        page_count = doc.page_count
        doc.close()
    except Exception as exc:
        raise OutputValidationError(f"Output PDF '{path}' could not be opened: {exc}") from exc

    if page_count < 1:
        raise OutputValidationError(f"Output PDF '{path}' has no pages.")


def validate_exists(path: Path) -> None:
    """Verify that *path* exists and has non-zero size.

    Args:
        path: Path to check.

    Raises:
        OutputValidationError: If the file does not exist or is empty.
    """
    if not path.exists():
        raise OutputValidationError(f"Output file '{path}' does not exist.")
    if path.stat().st_size == 0:
        raise OutputValidationError(f"Output file '{path}' is empty (zero bytes).")
