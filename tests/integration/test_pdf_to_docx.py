"""Integration tests for PDF to Word (.docx) conversion."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pymupdf as fitz
import pytest

from pdf_tool.adapters.pdf_to_docx import PdfToDocxAdapter
from pdf_tool.exceptions import InvalidInputError


def test_pdf_to_docx_conversion(tmp_path: Path) -> None:
    """PDF with text converts to a valid, readable .docx file."""
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 72), "Document Title", fontsize=16)
    p.insert_text((50, 100), "This is a paragraph converted from PDF to Word.", fontsize=11)
    doc.save(str(pdf_path))
    doc.close()

    docx_path = tmp_path / "sample.docx"
    adapter = PdfToDocxAdapter()
    result = adapter.convert(pdf_path, docx_path)

    assert result.output_path.exists()
    assert result.output_size_bytes > 0
    assert result.engine == "pdf2docx"

    # Verify output is a valid DOCX (valid ZIP archive with word/document.xml)
    with zipfile.ZipFile(str(docx_path), "r") as z:
        assert "word/document.xml" in z.namelist()


def test_pdf_to_docx_nonexistent_file(tmp_path: Path) -> None:
    """Converting nonexistent PDF raises InvalidInputError."""
    missing = tmp_path / "missing.pdf"
    docx_path = tmp_path / "out.docx"

    adapter = PdfToDocxAdapter()
    with pytest.raises(InvalidInputError):
        adapter.convert(missing, docx_path)
