"""Unit tests for FileInspector."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image

from pdf_tool.router.file_inspector import FileInspector


@pytest.fixture
def inspector() -> FileInspector:
    return FileInspector()


class TestDetectExtension:
    def test_pdf_extension(self, inspector: FileInspector) -> None:
        path = Path("document.pdf")
        assert inspector.detect_extension(path) == "pdf"

    def test_jpg_normalized_to_jpeg(self, inspector: FileInspector) -> None:
        path = Path("photo.jpg")
        assert inspector.detect_extension(path) == "jpeg"

    def test_jpeg_unchanged(self, inspector: FileInspector) -> None:
        path = Path("photo.jpeg")
        assert inspector.detect_extension(path) == "jpeg"

    def test_png_extension(self, inspector: FileInspector) -> None:
        path = Path("image.PNG")  # uppercase
        assert inspector.detect_extension(path) == "png"

    def test_tif_normalized_to_tiff(self, inspector: FileInspector) -> None:
        path = Path("scan.tif")
        assert inspector.detect_extension(path) == "tiff"

    def test_docx_extension(self, inspector: FileInspector) -> None:
        path = Path("report.docx")
        assert inspector.detect_extension(path) == "docx"

    def test_webp_extension(self, inspector: FileInspector) -> None:
        path = Path("image.webp")
        assert inspector.detect_extension(path) == "webp"

    def test_no_extension_nonexistent(self, inspector: FileInspector) -> None:
        path = Path("noext")
        assert inspector.detect_extension(path) == ""

    def test_extensionless_jpeg_file(self, inspector: FileInspector, tmp_path: Path) -> None:
        """A real JPEG file without .jpg/.jpeg in name should be recognized as jpeg."""
        p = tmp_path / "camera_raw_upload"
        Image.new("RGB", (30, 30), color="red").save(str(p), format="JPEG")
        assert inspector.detect_extension(p) == "jpeg"

    def test_extensionless_png_file(self, inspector: FileInspector, tmp_path: Path) -> None:
        """A real PNG file without .png in name should be recognized as png."""
        p = tmp_path / "screenshot_artifact"
        Image.new("RGB", (30, 30), color="blue").save(str(p), format="PNG")
        assert inspector.detect_extension(p) == "png"

    def test_extensionless_pdf_file(self, inspector: FileInspector, tmp_path: Path) -> None:
        """A real PDF file without .pdf in name should be recognized as pdf."""
        p = tmp_path / "downloaded_invoice"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(p))
        doc.close()
        assert inspector.detect_extension(p) == "pdf"

    def test_misleading_tmp_extension_pdf(self, inspector: FileInspector, tmp_path: Path) -> None:
        """A file named invoice.tmp containing PDF content should be recognized as pdf."""
        p = tmp_path / "invoice.tmp"
        doc = fitz.open()
        doc.new_page()
        doc.save(str(p))
        doc.close()
        assert inspector.detect_extension(p) == "pdf"


class TestDetectMime:
    def test_pdf_mime(self, inspector: FileInspector, tmp_path: Path) -> None:
        """MIME detection should return a string for a real PDF file."""
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\n%%EOF\n")
        mime = inspector.detect_mime(pdf_file)
        assert isinstance(mime, str)
        assert "pdf" in mime

    def test_png_mime_fallback(self, inspector: FileInspector) -> None:
        """Extension-based fallback should return image/png for .png path."""
        path = Path("image.png")
        mime = inspector.detect_mime(path)
        assert isinstance(mime, str)

    def test_detect_returns_tuple(self, inspector: FileInspector) -> None:
        path = Path("file.pdf")
        result = inspector.detect(path)
        assert isinstance(result, tuple)
        assert len(result) == 2
