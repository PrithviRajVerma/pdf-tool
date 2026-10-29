"""Integration tests for Image → PDF and PDF → Image conversions."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from PIL import Image

from pdf_tool.adapters.image_to_pdf import ImageToPdfAdapter
from pdf_tool.adapters.pdf_to_image import PdfToImageAdapter
from pdf_tool.utils.output_validator import validate_pdf


def _make_test_png(path: Path, color: tuple = (255, 0, 0), size: tuple = (100, 100)) -> Path:
    """Create a simple solid-color PNG for testing."""
    img = Image.new("RGB", size, color=color)
    img.save(str(path), format="PNG")
    return path


def _make_test_jpeg(path: Path, color: tuple = (0, 255, 0), size: tuple = (100, 100)) -> Path:
    """Create a simple solid-color JPEG for testing."""
    img = Image.new("RGB", size, color=color)
    img.save(str(path), format="JPEG")
    return path


class TestImageToPdf:
    def test_single_png_to_pdf(self, tmp_path: Path) -> None:
        """A single PNG should be converted to a valid single-page PDF."""
        png = _make_test_png(tmp_path / "test.png")
        out = tmp_path / "output.pdf"

        adapter = ImageToPdfAdapter()
        result = adapter.convert(png, out)

        assert result.output_path.exists()
        validate_pdf(result.output_path)  # Should not raise

        doc = fitz.open(str(result.output_path))
        assert doc.page_count == 1
        doc.close()

    def test_single_jpeg_to_pdf(self, tmp_path: Path) -> None:
        """A single JPEG should convert successfully."""
        jpg = _make_test_jpeg(tmp_path / "test.jpg")
        out = tmp_path / "output.pdf"

        adapter = ImageToPdfAdapter()
        result = adapter.convert(jpg, out)

        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 0

    def test_multi_image_to_pdf(self, tmp_path: Path) -> None:
        """Multiple images should be merged into a multi-page PDF."""
        img1 = _make_test_png(tmp_path / "img1.png", color=(255, 0, 0))
        img2 = _make_test_png(tmp_path / "img2.png", color=(0, 255, 0))
        img3 = _make_test_png(tmp_path / "img3.png", color=(0, 0, 255))
        out = tmp_path / "merged.pdf"

        adapter = ImageToPdfAdapter()
        result = adapter.convert(img1, out, extra_inputs=[img2, img3])

        assert result.output_path.exists()
        validate_pdf(result.output_path)

        doc = fitz.open(str(result.output_path))
        assert doc.page_count == 3
        doc.close()

    def test_rgba_image_to_pdf(self, tmp_path: Path) -> None:
        """RGBA images should be composited to RGB before PDF conversion."""
        rgba_path = tmp_path / "rgba.png"
        img = Image.new("RGBA", (100, 100), color=(0, 128, 255, 128))
        img.save(str(rgba_path), format="PNG")
        out = tmp_path / "output.pdf"

        adapter = ImageToPdfAdapter()
        result = adapter.convert(rgba_path, out)
        assert result.output_path.exists()
        validate_pdf(result.output_path)

    def test_result_metadata(self, tmp_path: Path) -> None:
        """ConversionResult should have correct engine and positive sizes."""
        png = _make_test_png(tmp_path / "test.png")
        out = tmp_path / "output.pdf"

        adapter = ImageToPdfAdapter()
        result = adapter.convert(png, out)

        assert result.engine == "Pillow"
        assert result.input_size_bytes > 0
        assert result.output_size_bytes > 0
        assert result.duration_seconds >= 0


class TestPdfToImage:
    def _make_test_pdf(self, path: Path, num_pages: int = 2) -> Path:
        """Create a minimal multi-page PDF using PyMuPDF."""
        doc = fitz.open()
        for i in range(num_pages):
            page = doc.new_page(width=100, height=100)
            page.insert_text((10, 50), f"Page {i + 1}")
        doc.save(str(path))
        doc.close()
        return path

    def test_pdf_to_png_single_page(self, tmp_path: Path) -> None:
        """Single-page PDF → PNG should produce one file at output_path."""
        pdf = self._make_test_pdf(tmp_path / "single.pdf", num_pages=1)
        out = tmp_path / "output.png"

        adapter = PdfToImageAdapter()
        result = adapter.convert(pdf, out)
        assert result.output_path.exists()

        assert result.output_path.exists()
        img = Image.open(str(result.output_path))
        assert img.format in ("PNG", "JPEG")

    def test_pdf_to_png_multi_page(self, tmp_path: Path) -> None:
        """Multi-page PDF → PNG should produce numbered files."""
        pdf = self._make_test_pdf(tmp_path / "multi.pdf", num_pages=3)
        out = tmp_path / "output.png"

        adapter = PdfToImageAdapter()
        result = adapter.convert(pdf, out)
        assert result.output_path.exists()

        # Expect output_p1.png, output_p2.png, output_p3.png
        for i in range(1, 4):
            p = tmp_path / f"output_p{i}.png"
            assert p.exists(), f"Expected {p} to exist"

    def test_pdf_to_png_page_range(self, tmp_path: Path) -> None:
        """Page range '1-2' from a 3-page PDF should produce 2 files."""
        pdf = self._make_test_pdf(tmp_path / "three.pdf", num_pages=3)
        out = tmp_path / "output.png"

        adapter = PdfToImageAdapter()
        adapter.convert(pdf, out, pages="1-2")

        assert (tmp_path / "output_p1.png").exists()
        assert (tmp_path / "output_p2.png").exists()
        assert not (tmp_path / "output_p3.png").exists()

    def test_round_trip_image_pdf_image(self, tmp_path: Path) -> None:
        """PNG → PDF → PNG round-trip should succeed."""
        # Create PNG
        src_png = _make_test_png(tmp_path / "source.png")
        pdf_path = tmp_path / "round_trip.pdf"
        img_out = tmp_path / "result.png"

        # PNG → PDF
        img_adapter = ImageToPdfAdapter()
        img_adapter.convert(src_png, pdf_path)
        validate_pdf(pdf_path)

        # PDF → PNG
        pdf_adapter = PdfToImageAdapter()
        result = pdf_adapter.convert(pdf_path, img_out)
        assert result.output_path.exists()
        assert result.output_path.stat().st_size > 0
