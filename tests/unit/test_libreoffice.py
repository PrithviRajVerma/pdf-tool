"""Unit tests for LibreOffice subprocess wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pdf_tool.exceptions import ConversionFailedError, MissingDependencyError
from pdf_tool.utils.libreoffice import find_libreoffice_binary, run_libreoffice_convert


def test_find_libreoffice_binary() -> None:
    """find_libreoffice_binary returns a string if found, or None."""
    result = find_libreoffice_binary()
    assert result is None or isinstance(result, str)


def test_missing_libreoffice_raises(tmp_path: Path) -> None:
    """When LibreOffice is missing, run_libreoffice_convert raises MissingDependencyError."""
    dummy_in = tmp_path / "test.docx"
    dummy_in.write_text("dummy")
    dummy_out = tmp_path / "test.pdf"

    with patch("pdf_tool.utils.libreoffice.find_libreoffice_binary", return_value=None):
        with pytest.raises(MissingDependencyError) as exc_info:
            run_libreoffice_convert(dummy_in, dummy_out)
        assert exc_info.value.dep_name == "soffice"


def test_libreoffice_timeout(tmp_path: Path) -> None:
    """LibreOffice timeout raises ConversionFailedError."""
    dummy_in = tmp_path / "test.docx"
    dummy_in.write_text("dummy")
    dummy_out = tmp_path / "test.pdf"

    with patch(
        "pdf_tool.utils.libreoffice.find_libreoffice_binary", return_value="/usr/bin/soffice"
    ):
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="soffice", timeout=5.0)
        ):
            with pytest.raises(ConversionFailedError) as exc_info:
                run_libreoffice_convert(dummy_in, dummy_out, timeout=5.0)
            assert "timed out" in str(exc_info.value)


def test_libreoffice_nonzero_exit(tmp_path: Path) -> None:
    """Non-zero exit code raises ConversionFailedError."""
    dummy_in = tmp_path / "test.docx"
    dummy_in.write_text("dummy")
    dummy_out = tmp_path / "test.pdf"

    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stderr = "Corrupted document format"
    mock_proc.stdout = ""

    with patch(
        "pdf_tool.utils.libreoffice.find_libreoffice_binary", return_value="/usr/bin/soffice"
    ):
        with patch("subprocess.run", return_value=mock_proc):
            with pytest.raises(ConversionFailedError) as exc_info:
                run_libreoffice_convert(dummy_in, dummy_out)
            assert "Corrupted document format" in str(exc_info.value)


def test_libreoffice_successful_conversion(tmp_path: Path) -> None:
    """Successful LibreOffice conversion moves generated file to output_path."""
    dummy_in = tmp_path / "test.docx"
    dummy_in.write_text("dummy")
    dummy_out = tmp_path / "output.pdf"

    def fake_subprocess_run(cmd, **kwargs):
        # Find the --outdir argument and create a dummy .pdf file
        out_dir_idx = cmd.index("--outdir") + 1
        out_dir = Path(cmd[out_dir_idx])
        (out_dir / "test.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stderr = ""
        mock_res.stdout = ""
        return mock_res

    with patch(
        "pdf_tool.utils.libreoffice.find_libreoffice_binary", return_value="/usr/bin/soffice"
    ):
        with patch("subprocess.run", side_effect=fake_subprocess_run):
            result = run_libreoffice_convert(dummy_in, dummy_out)
            assert result == dummy_out
            assert dummy_out.exists()
            assert dummy_out.read_bytes().startswith(b"%PDF")
