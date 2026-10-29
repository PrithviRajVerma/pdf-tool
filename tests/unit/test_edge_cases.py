"""Unit tests for edge cases, corruption, and failure conditions."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf_tool.adapters.merge import MergeAdapter
from pdf_tool.adapters.split import SplitAdapter
from pdf_tool.exceptions import (
    OutputValidationError,
    PdfToolError,
    UnsupportedConversionError,
)
from pdf_tool.router.file_inspector import FileInspector
from pdf_tool.router.registry import registry
from pdf_tool.utils.output_validator import validate_pdf


def test_validate_pdf_nonexistent(tmp_path: Path):
    nonexistent = tmp_path / "does_not_exist.pdf"
    with pytest.raises(OutputValidationError, match="does not exist"):
        validate_pdf(nonexistent)


def test_validate_pdf_zero_bytes(tmp_path: Path):
    empty_file = tmp_path / "empty.pdf"
    empty_file.write_bytes(b"")
    with pytest.raises(OutputValidationError, match="empty"):
        validate_pdf(empty_file)


def test_validate_pdf_corrupt_content(tmp_path: Path):
    corrupt_file = tmp_path / "corrupt.pdf"
    corrupt_file.write_text("This is definitely not a PDF document format.")
    with pytest.raises(OutputValidationError, match="could not be opened"):
        validate_pdf(corrupt_file)


def test_file_inspector_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.txt"
    empty.write_bytes(b"")
    inspector = FileInspector()
    mime, ext = inspector.detect(empty)
    assert ext == "txt"


def test_registry_unsupported_pair():
    with pytest.raises(UnsupportedConversionError) as exc_info:
        registry.lookup("unsupported_in", "unsupported_out")
    assert exc_info.value.input_fmt == "unsupported_in"
    assert exc_info.value.output_fmt == "unsupported_out"


def test_split_adapter_nonexistent(tmp_path: Path):
    adapter = SplitAdapter()
    with pytest.raises(PdfToolError):
        adapter.split(tmp_path / "ghost.pdf", tmp_path)


def test_merge_adapter_empty_list(tmp_path: Path):
    adapter = MergeAdapter()
    with pytest.raises(PdfToolError):
        adapter.merge([], tmp_path / "out.pdf")
