"""Integration tests for PDF to Markdown and plain text extraction."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pdf_tool.adapters.pdf_to_text import PdfToTextAdapter
from pdf_tool.exceptions import InvalidInputError


def _create_sample_pdf(pdf_path: Path) -> None:
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 60), "Architecture Summary", fontsize=18)
    p.insert_text((50, 90), "This is section one describing the system.", fontsize=11)
    doc.save(str(pdf_path))
    doc.close()


def test_pdf_to_markdown(tmp_path: Path) -> None:
    """PDF content extracts into Markdown preserving headings."""
    pdf_path = tmp_path / "doc.pdf"
    _create_sample_pdf(pdf_path)

    md_path = tmp_path / "doc.md"
    adapter = PdfToTextAdapter()
    result = adapter.convert(pdf_path, md_path)

    assert result.output_path.exists()
    assert result.engine == "pymupdf4llm"

    content = md_path.read_text(encoding="utf-8")
    assert "Architecture Summary" in content
    assert "describing the system" in content


def test_pdf_to_plain_text(tmp_path: Path) -> None:
    """PDF content extracts into clean plain text."""
    pdf_path = tmp_path / "doc.pdf"
    _create_sample_pdf(pdf_path)

    txt_path = tmp_path / "doc.txt"
    adapter = PdfToTextAdapter()
    result = adapter.convert(pdf_path, txt_path)

    assert result.output_path.exists()
    content = txt_path.read_text(encoding="utf-8")
    assert "Architecture Summary" in content


def test_pdf_to_text_nonexistent_file(tmp_path: Path) -> None:
    """Converting nonexistent PDF raises InvalidInputError."""
    missing = tmp_path / "nonexistent.pdf"
    md_path = tmp_path / "doc.md"

    adapter = PdfToTextAdapter()
    with pytest.raises(InvalidInputError):
        adapter.convert(missing, md_path)
