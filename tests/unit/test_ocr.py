"""Unit tests for OCR adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from pdf_tool.adapters.ocr import OcrAdapter
from pdf_tool.exceptions import MissingDependencyError
from pdf_tool.main import app
from pdf_tool.utils.dependency_checker import DependencyStatus

runner = CliRunner()


def test_ocr_missing_tesseract_raises(tmp_path: Path) -> None:
    """When Tesseract is missing, OcrAdapter raises MissingDependencyError."""
    dummy_pdf = tmp_path / "scanned.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    out_pdf = tmp_path / "out.pdf"

    with patch(
        "pdf_tool.adapters.ocr.check", return_value=DependencyStatus("tesseract", False, None)
    ):
        adapter = OcrAdapter()
        with pytest.raises(MissingDependencyError) as exc_info:
            adapter.convert(dummy_pdf, out_pdf)
        assert exc_info.value.dep_name == "tesseract"
        assert "ubuntu" in exc_info.value.install_hints
        assert "arch" in exc_info.value.install_hints


def test_ocr_success_mocked(tmp_path: Path) -> None:
    """Mocking ocrmypdf.ocr verifies arguments and result metadata."""
    dummy_pdf = tmp_path / "scanned.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%%EOF")
    out_pdf = tmp_path / "out.pdf"

    def fake_ocr(**kwargs):
        kwargs["output_file"].write_bytes(b"%PDF-1.4\nsearchable\n%%EOF")
        return 0

    with patch(
        "pdf_tool.adapters.ocr.check",
        return_value=DependencyStatus("tesseract", True, "/usr/bin/tesseract"),
    ):
        with patch("ocrmypdf.ocr", side_effect=fake_ocr) as mock_ocr:
            adapter = OcrAdapter()
            result = adapter.convert(dummy_pdf, out_pdf, lang="eng", force=True)

            mock_ocr.assert_called_once()
            assert result.output_path == out_pdf
            assert result.engine == "OCRmyPDF (Tesseract)"


def test_ocr_cli_command_missing_dep(tmp_path: Path) -> None:
    """Running `pdf ocr` without tesseract displays install commands."""
    dummy_pdf = tmp_path / "scanned.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4\n%%EOF")

    with patch(
        "pdf_tool.adapters.ocr.check", return_value=DependencyStatus("tesseract", False, None)
    ):
        result = runner.invoke(app, ["ocr", str(dummy_pdf)])
        assert result.exit_code == 1
        assert "Missing dependency" in result.output
        assert "tesseract" in result.output
