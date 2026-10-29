"""Tests for Office to PDF adapter."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from pdf_tool.adapters.office_to_pdf import OfficeToPdfAdapter
from pdf_tool.router.registry import registry


def test_office_adapter_registered_formats() -> None:
    """OfficeToPdfAdapter should be registered for all standard office extensions."""
    for fmt in ("docx", "doc", "odt", "rtf", "xlsx", "xls", "ods", "pptx", "ppt", "odp"):
        adapter_cls = registry.lookup(fmt, "pdf")
        assert adapter_cls is OfficeToPdfAdapter


def test_office_adapter_convert_invokes_libreoffice(tmp_path: Path) -> None:
    """OfficeToPdfAdapter invokes run_libreoffice_convert with correct parameters."""
    docx_file = tmp_path / "document.docx"
    docx_file.write_bytes(b"dummy docx bytes")
    out_pdf = tmp_path / "document.pdf"

    adapter = OfficeToPdfAdapter()
    assert adapter.required_system_deps == ["soffice"]
    assert adapter.engine_name == "LibreOffice"

    def fake_run(in_p, out_p, timeout=60.0):
        out_p.write_bytes(b"%PDF-1.4\n%%EOF")
        return out_p

    with patch(
        "pdf_tool.adapters.office_to_pdf.run_libreoffice_convert", side_effect=fake_run
    ) as mock_run:
        result = adapter.convert(docx_file, out_pdf)
        mock_run.assert_called_once_with(docx_file, out_pdf, timeout=60.0)
        assert result.output_path == out_pdf
        assert result.engine == "LibreOffice"
