"""Integration tests for HTML to PDF conversion."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pdf_tool.adapters.html_to_pdf import HtmlToPdfAdapter
from pdf_tool.exceptions import InvalidInputError
from pdf_tool.utils.output_validator import validate_pdf


def test_html_basic_to_pdf(tmp_path: Path) -> None:
    """Basic HTML document converts to a valid PDF."""
    html_file = tmp_path / "index.html"
    html_file.write_text(
        """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <style>
        h1 { color: #2c5282; font-family: sans-serif; }
        p { font-size: 14px; }
    </style>
</head>
<body>
    <h1>Official Statement</h1>
    <p>This document has been generated automatically.</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    out_pdf = tmp_path / "page.pdf"

    adapter = HtmlToPdfAdapter()
    result = adapter.convert(html_file, out_pdf)

    assert result.output_path.exists()
    validate_pdf(result.output_path)

    doc = fitz.open(str(result.output_path))
    assert doc.page_count >= 1
    text = doc[0].get_text()
    assert "Official Statement" in text
    doc.close()


def test_html_nonexistent_file(tmp_path: Path) -> None:
    """Converting nonexistent HTML file raises InvalidInputError."""
    missing_file = tmp_path / "missing.html"
    out_pdf = tmp_path / "out.pdf"

    adapter = HtmlToPdfAdapter()
    with pytest.raises(InvalidInputError):
        adapter.convert(missing_file, out_pdf)
