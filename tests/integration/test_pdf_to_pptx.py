"""Integration tests for PDF to PowerPoint presentation (.pptx) conversion."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image
from pptx import Presentation
from typer.testing import CliRunner

from pdf_tool.adapters.pdf_to_pptx import PdfToPptxAdapter
from pdf_tool.exceptions import InvalidInputError
from pdf_tool.main import app

runner = CliRunner()


def test_pdf_to_pptx_editable_conversion(tmp_path: Path) -> None:
    """PDF with text converts to an editable .pptx file with text frames."""
    pdf_path = tmp_path / "presentation.pdf"
    doc = fitz.open()
    page = doc.new_page(width=720, height=405)  # 16:9 ratio
    page.insert_text((50, 60), "Quarterly Business Review", fontsize=24)
    page.insert_text((50, 100), "Key accomplishments and roadmap highlights.", fontsize=14)
    doc.save(str(pdf_path))
    doc.close()

    pptx_path = tmp_path / "presentation.pptx"
    adapter = PdfToPptxAdapter()
    result = adapter.convert(pdf_path, pptx_path, mode="editable")

    assert result.output_path.exists()
    assert result.output_size_bytes > 0
    assert result.engine == "python-pptx + PyMuPDF"

    # Verify PPTX is a valid zip archive with ppt/presentation.xml
    with zipfile.ZipFile(str(pptx_path), "r") as z:
        assert "ppt/presentation.xml" in z.namelist()

    # Verify presentation structure and shapes
    prs = Presentation(str(pptx_path))
    assert len(prs.slides) == 1
    slide = prs.slides[0]
    extracted_texts = [s.text_frame.text for s in slide.shapes if s.has_text_frame]
    joined_text = " ".join(extracted_texts)
    assert "Quarterly Business Review" in joined_text
    assert "Key accomplishments" in joined_text


def test_pdf_to_pptx_with_images(tmp_path: Path) -> None:
    """PDF with embedded images converts to PPTX containing picture shapes."""
    pdf_path = tmp_path / "slides_with_img.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.insert_text((50, 50), "Slide with an embedded chart", fontsize=18)

    # Insert a 100x100 test image
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page.insert_image(fitz.Rect(50, 80, 200, 230), stream=buf.getvalue())

    doc.save(str(pdf_path))
    doc.close()

    pptx_path = tmp_path / "slides_with_img.pptx"
    adapter = PdfToPptxAdapter()
    result = adapter.convert(pdf_path, pptx_path)

    assert result.output_path.exists()
    prs = Presentation(str(pptx_path))
    slide = prs.slides[0]
    # Check that at least one shape is a picture
    shape_types = [shape.shape_type for shape in slide.shapes]
    # In python-pptx, MSO_SHAPE_TYPE.PICTURE has value 13
    assert any(getattr(st, "value", st) == 13 for st in shape_types)


def test_pdf_to_pptx_visual_mode(tmp_path: Path) -> None:
    """Visual mode renders high-resolution slide images directly onto slides."""
    pdf_path = tmp_path / "visual.pdf"
    doc = fitz.open()
    page = doc.new_page(width=800, height=450)
    page.insert_text((100, 100), "Visual Mode Slide", fontsize=20)
    doc.save(str(pdf_path))
    doc.close()

    pptx_path = tmp_path / "visual.pptx"
    adapter = PdfToPptxAdapter()
    result = adapter.convert(pdf_path, pptx_path, mode="visual", dpi=150)

    assert result.output_path.exists()
    prs = Presentation(str(pptx_path))
    assert len(prs.slides) == 1
    # In visual mode, slide has a single full-slide picture shape
    slide = prs.slides[0]
    assert len(slide.shapes) == 1
    shape = slide.shapes[0]
    assert getattr(shape.shape_type, "value", shape.shape_type) == 13


def test_pdf_to_pptx_page_selection(tmp_path: Path) -> None:
    """Pages option converts only the selected page range."""
    pdf_path = tmp_path / "multipage.pdf"
    doc = fitz.open()
    for i in range(1, 6):
        page = doc.new_page(width=600, height=400)
        page.insert_text((50, 50), f"Slide Page {i}", fontsize=18)
    doc.save(str(pdf_path))
    doc.close()

    pptx_path = tmp_path / "pages_selected.pptx"
    adapter = PdfToPptxAdapter()
    # Select only pages 2 and 4
    result = adapter.convert(pdf_path, pptx_path, pages="2,4")

    assert result.output_path.exists()
    prs = Presentation(str(pptx_path))
    assert len(prs.slides) == 2
    slide0_text = " ".join([s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame])
    slide1_text = " ".join([s.text_frame.text for s in prs.slides[1].shapes if s.has_text_frame])
    assert "Slide Page 2" in slide0_text
    assert "Slide Page 4" in slide1_text


def test_pdf_to_pptx_scanned_fallback(tmp_path: Path) -> None:
    """PDF without selectable text falls back to visual slide image instead of blank slide."""
    pdf_path = tmp_path / "scanned.pdf"
    doc = fitz.open()
    # Create empty page without selectable text
    doc.new_page(width=600, height=400)
    doc.save(str(pdf_path))
    doc.close()

    pptx_path = tmp_path / "scanned.pptx"
    adapter = PdfToPptxAdapter()
    result = adapter.convert(pdf_path, pptx_path)

    assert result.output_path.exists()
    prs = Presentation(str(pptx_path))
    assert len(prs.slides) == 1
    # Check that picture was added
    assert len(prs.slides[0].shapes) == 1


def test_pdf_to_pptx_nonexistent_file(tmp_path: Path) -> None:
    """Nonexistent input raises InvalidInputError."""
    missing = tmp_path / "missing.pdf"
    out = tmp_path / "out.pptx"
    adapter = PdfToPptxAdapter()
    with pytest.raises(InvalidInputError):
        adapter.convert(missing, out)


def test_pdf_to_pptx_cli_convert(tmp_path: Path) -> None:
    """CLI convert command supports --to pptx."""
    pdf_path = tmp_path / "deck.pdf"
    doc = fitz.open()
    page = doc.new_page(width=720, height=405)
    page.insert_text((60, 60), "CLI Deck Title", fontsize=22)
    doc.save(str(pdf_path))
    doc.close()

    out_pptx = tmp_path / "deck.pptx"
    res = runner.invoke(app, ["convert", str(pdf_path), "--to", "pptx", "-o", str(out_pptx)])
    assert res.exit_code == 0
    assert out_pptx.exists()
    prs = Presentation(str(out_pptx))
    assert len(prs.slides) == 1
