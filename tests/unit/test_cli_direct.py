"""Unit tests for direct conversion and CLI aliases."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
from PIL import Image
from typer.testing import CliRunner

from pdf_tool.main import app

runner = CliRunner()


def test_direct_image_to_pdf(tmp_path: Path) -> None:
    """Running `pdf photo.png` directly converts to `photo.pdf` without subcommand."""
    img_path = tmp_path / "photo.png"
    Image.new("RGB", (50, 50), color="blue").save(str(img_path))

    result = runner.invoke(app, [str(img_path)])
    assert result.exit_code == 0
    assert (tmp_path / "photo.pdf").exists()


def test_direct_image_to_custom_pdf(tmp_path: Path) -> None:
    """Running `pdf photo.png output.pdf` uses positional output."""
    img_path = tmp_path / "photo.png"
    out_path = tmp_path / "custom.pdf"
    Image.new("RGB", (50, 50), color="green").save(str(img_path))

    result = runner.invoke(app, [str(img_path), str(out_path)])
    assert result.exit_code == 0
    assert out_path.exists()


def test_direct_multi_image_merge(tmp_path: Path) -> None:
    """Running `pdf img1.jpg img2.png combined.pdf` merges images."""
    p1 = tmp_path / "img1.jpg"
    p2 = tmp_path / "img2.png"
    out = tmp_path / "combined.pdf"
    Image.new("RGB", (50, 50), color="red").save(str(p1))
    Image.new("RGB", (50, 50), color="yellow").save(str(p2))

    result = runner.invoke(app, [str(p1), str(p2), str(out)])
    assert result.exit_code == 0
    assert out.exists()


def test_direct_extensionless_image_to_pdf(tmp_path: Path) -> None:
    """A file with no extension containing JPEG image data converts directly to .pdf."""
    img_path = tmp_path / "raw_camera_scan"
    Image.new("RGB", (60, 60), color="orange").save(str(img_path), format="JPEG")

    result = runner.invoke(app, [str(img_path)])
    assert result.exit_code == 0
    assert (tmp_path / "raw_camera_scan.pdf").exists()


def test_direct_extensionless_pdf_to_images(tmp_path: Path) -> None:
    """A file with no extension containing PDF data converts directly to .png."""
    pdf_path = tmp_path / "invoice_blob"
    doc = fitz.open()
    doc.new_page()
    doc.save(str(pdf_path))
    doc.close()

    result = runner.invoke(app, [str(pdf_path)])
    assert result.exit_code == 0
    assert (tmp_path / "invoice_blob.png").exists()


def test_alias_compress(tmp_path: Path) -> None:
    """`pdf z file.pdf` invokes compress."""
    img_path = tmp_path / "dummy.png"
    pdf_path = tmp_path / "test.pdf"
    Image.new("RGB", (50, 50), color="red").save(str(img_path))
    runner.invoke(app, [str(img_path), str(pdf_path)])

    result = runner.invoke(app, ["z", str(pdf_path)])
    assert result.exit_code == 0
    assert (tmp_path / "test_compressed.pdf").exists()


def test_alias_doctor() -> None:
    """`pdf doc` invokes doctor."""
    result = runner.invoke(app, ["doc"])
    assert result.exit_code == 0
    assert "System Dependencies" in result.output
