"""Integration tests for universal compression (Images, Office docs, and PDFs)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from pdf_tool.adapters.compress import CompressAdapter
from pdf_tool.exceptions import InvalidInputError
from pdf_tool.main import app

runner = CliRunner()


def _make_test_image(path: Path, width: int = 1200, height: int = 800) -> Path:
    """Generate a test image with gradients and color variations."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    for x in range(0, width, 20):
        for y in range(0, height, 20):
            img.putpixel((x, y), (x % 255, y % 255, (x + y) % 255))
    ext = path.suffix.lower().lstrip(".")
    fmt = "JPEG" if ext in ("jpg", "jpeg") else "PNG"
    img.save(path, format=fmt)
    return path


def test_compress_jpeg_image(tmp_path: Path) -> None:
    """Compress JPEG image with quality reduction."""
    img_path = _make_test_image(tmp_path / "large.jpg", 1600, 1200)
    out_path = tmp_path / "compressed.jpg"

    adapter = CompressAdapter()
    result = adapter.compress(img_path, out_path, level="high")

    assert result.output_path.exists()
    assert result.output_size_bytes > 0
    assert result.engine == "Pillow"


def test_compress_png_quantization(tmp_path: Path) -> None:
    """Compress PNG with high level triggers 8-bit quantization."""
    img_path = _make_test_image(tmp_path / "large.png", 800, 600)
    out_path = tmp_path / "compressed.png"

    adapter = CompressAdapter()
    result = adapter.compress(img_path, out_path, level="high")

    assert result.output_path.exists()
    assert result.output_size_bytes > 0
    # Quantized 8-bit PNG is generally much smaller than 24-bit PNG
    assert result.output_size_bytes <= result.input_size_bytes


def test_compress_image_max_dim(tmp_path: Path) -> None:
    """Explicit max_dim downscales the image dimensions."""
    img_path = _make_test_image(tmp_path / "to_downscale.jpg", 2000, 1000)
    out_path = tmp_path / "downscaled.jpg"

    adapter = CompressAdapter()
    result = adapter.compress(img_path, out_path, level="medium", max_dim=800)

    assert result.output_path.exists()
    with Image.open(out_path) as im:
        assert max(im.size) <= 800


def test_compress_docx_office_media(tmp_path: Path) -> None:
    """Compress Office DOCX document containing media images."""
    docx_path = tmp_path / "sample.docx"
    with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", "<Types></Types>")
        zf.writestr("word/document.xml", "<w:document></w:document>")
        # Embedded large image in word/media/
        img = Image.new("RGB", (1500, 1500), color=(200, 50, 50))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        zf.writestr("word/media/image1.png", buf.getvalue())

    out_path = tmp_path / "compressed.docx"
    adapter = CompressAdapter()
    result = adapter.compress(docx_path, out_path, level="high")

    assert result.output_path.exists()
    assert result.engine == "ZipDeflate + Pillow"
    # Verify valid zip with original structure intact
    with zipfile.ZipFile(out_path, "r") as zf:
        assert "word/document.xml" in zf.namelist()
        assert "word/media/image1.png" in zf.namelist()


def test_compress_unsupported_format(tmp_path: Path) -> None:
    """Attempting to compress unsupported file formats raises InvalidInputError."""
    dummy = tmp_path / "file.xyz"
    dummy.write_text("unsupported")
    out = tmp_path / "out.xyz"

    adapter = CompressAdapter()
    with pytest.raises(InvalidInputError):
        adapter.compress(dummy, out)


def test_cli_compress_image(tmp_path: Path) -> None:
    """CLI compress command on image file."""
    img_path = _make_test_image(tmp_path / "cli_photo.jpg", 600, 400)
    out_path = tmp_path / "cli_photo_comp.jpg"

    res = runner.invoke(app, ["compress", str(img_path), "--level", "high", "-o", str(out_path)])
    assert res.exit_code == 0
    assert out_path.exists()


def test_compress_target_size(tmp_path: Path) -> None:
    """Target size budget forces iterative compression below threshold."""
    img_path = _make_test_image(tmp_path / "large_photo.jpg", 1600, 1200)
    out_path = tmp_path / "budget_photo.jpg"

    adapter = CompressAdapter()
    target_bytes = 40 * 1024  # 40 KB
    result = adapter.compress(img_path, out_path, target_size_bytes=target_bytes)

    assert result.output_path.exists()
    assert result.output_size_bytes <= target_bytes


def test_cli_compress_to_webp(tmp_path: Path) -> None:
    """CLI compress with --to-webp outputs WebP image."""
    img_path = _make_test_image(tmp_path / "convert_me.png", 600, 400)
    out_dir = tmp_path / "webp_out"

    res = runner.invoke(app, ["compress", str(img_path), "--to-webp", "--output-dir", str(out_dir)])
    assert res.exit_code == 0
    expected = out_dir / "convert_me_compressed.webp"
    assert expected.exists()


def test_cli_batch_compress(tmp_path: Path) -> None:
    """CLI batch compress processes multiple files in parallel."""
    img1 = _make_test_image(tmp_path / "b1.jpg", 400, 300)
    img2 = _make_test_image(tmp_path / "b2.jpg", 400, 300)
    out_dir = tmp_path / "batch_out"

    res = runner.invoke(
        app,
        ["compress", str(img1), str(img2), "--output-dir", str(out_dir), "--parallel", "-w", "2"],
    )
    assert res.exit_code == 0
    assert (out_dir / "b1_compressed.jpg").exists()
    assert (out_dir / "b2_compressed.jpg").exists()


def test_size_parser_units() -> None:
    """Unit test for size string parser."""
    from pdf_tool.utils.size_parser import parse_size_bytes

    assert parse_size_bytes("500B") == 500
    assert parse_size_bytes("1KB") == 1024
    assert parse_size_bytes("2MB") == 2 * 1024 * 1024
    assert parse_size_bytes("1.5GB") == int(1.5 * 1024 * 1024 * 1024)

    with pytest.raises(ValueError):
        parse_size_bytes("invalid_size")
