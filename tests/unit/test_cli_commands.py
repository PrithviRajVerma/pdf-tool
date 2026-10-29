"""Comprehensive tests for all Typer CLI commands using CliRunner."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from pdf_tool.main import app

runner = CliRunner()


def _make_png(path: Path) -> Path:
    img = Image.new("RGB", (60, 60), color=(50, 100, 150))
    img.save(str(path), format="PNG")
    return path


def test_cli_doctor():
    res = runner.invoke(app, ["doctor"])
    assert res.exit_code == 0
    assert "System Dependencies" in res.output
    assert "Pure-Python Adapters" in res.output


def test_cli_doctor_alias():
    res = runner.invoke(app, ["doc"])
    assert res.exit_code == 0
    assert "System Dependencies" in res.output


def test_cli_config_commands(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    # config path
    res = runner.invoke(app, ["config", "path"])
    assert res.exit_code == 0

    # config show
    res = runner.invoke(app, ["config", "show"])
    assert res.exit_code == 0
    assert "Active Configuration" in res.output

    # config set
    res = runner.invoke(app, ["config", "set", "defaults.image_dpi", "220"])
    assert res.exit_code == 0
    assert "defaults.image_dpi = 220" in res.output

    # config get
    res = runner.invoke(app, ["config", "get", "defaults.image_dpi"])
    assert res.exit_code == 0
    assert "220" in res.output

    # config get invalid key
    res = runner.invoke(app, ["config", "get", "nonexistent.fake_key"])
    assert res.exit_code == 1

    # config reset key
    res = runner.invoke(app, ["config", "reset", "--key", "defaults.image_dpi"])
    assert res.exit_code == 0

    # config reset all
    res = runner.invoke(app, ["config", "reset"])
    assert res.exit_code == 0
    assert "factory defaults" in res.output


def test_cli_merge_insufficient_files():
    res = runner.invoke(app, ["merge", "single_file.pdf"])
    assert res.exit_code == 1
    assert "At least two PDF files are required" in res.output


def test_cli_merge_nonexistent_files(tmp_path: Path):
    res = runner.invoke(app, ["merge", str(tmp_path / "a.pdf"), str(tmp_path / "b.pdf")])
    assert res.exit_code == 1
    assert "File not found" in res.output


def test_cli_split_nonexistent_file(tmp_path: Path):
    res = runner.invoke(app, ["split", str(tmp_path / "missing.pdf")])
    assert res.exit_code == 1
    assert "File not found" in res.output


def test_cli_split_mutually_exclusive(tmp_path: Path):
    dummy = tmp_path / "dummy.pdf"
    dummy.write_text("content")
    res = runner.invoke(app, ["split", str(dummy), "--pages", "1-2", "--every", "2"])
    assert res.exit_code == 1
    assert "mutually exclusive" in res.output


def test_cli_compress_nonexistent_file(tmp_path: Path):
    res = runner.invoke(app, ["compress", str(tmp_path / "missing.pdf")])
    assert res.exit_code == 1
    assert "File not found" in res.output


def test_cli_compress_invalid_level(tmp_path: Path):
    dummy = tmp_path / "dummy.pdf"
    dummy.write_text("content")
    res = runner.invoke(app, ["compress", str(dummy), "--level", "ultra_extreme"])
    assert res.exit_code == 1
    assert "Invalid level" in res.output


def test_cli_ocr_nonexistent_file(tmp_path: Path):
    res = runner.invoke(app, ["ocr", str(tmp_path / "missing.pdf")])
    assert res.exit_code == 1
    assert "File not found" in res.output


def test_cli_convert_no_args():
    res = runner.invoke(app, ["convert"])
    assert res.exit_code != 0


def test_cli_convert_nonexistent_input(tmp_path: Path):
    res = runner.invoke(app, ["convert", str(tmp_path / "missing.png")])
    assert res.exit_code == 1
    assert "File not found" in res.output


def test_cli_convert_markdown_to_pdf(tmp_path: Path):
    md = tmp_path / "doc.md"
    md.write_text("# Hello Typer\nThis is a CLI test.")
    out_pdf = tmp_path / "doc.pdf"

    res = runner.invoke(app, ["convert", str(md), "-o", str(out_pdf)])
    assert res.exit_code == 0
    assert out_pdf.exists()
    assert "Conversion Complete" in res.output


def test_cli_direct_convert_shortcut(tmp_path: Path):
    png = _make_png(tmp_path / "shortcut.png")
    out_pdf = tmp_path / "shortcut.pdf"

    # Direct syntax without subcommand: pdf shortcut.png shortcut.pdf
    res = runner.invoke(app, [str(png), str(out_pdf)])
    assert res.exit_code == 0
    assert out_pdf.exists()


def test_cli_merge_success(tmp_path: Path):
    from pdf_tool.adapters.image_to_pdf import ImageToPdfAdapter

    p1 = tmp_path / "p1.pdf"
    p2 = tmp_path / "p2.pdf"
    img1 = _make_png(tmp_path / "i1.png")
    img2 = _make_png(tmp_path / "i2.png")
    adapter = ImageToPdfAdapter()
    adapter.convert(img1, p1)
    adapter.convert(img2, p2)

    merged = tmp_path / "merged.pdf"
    res = runner.invoke(app, ["merge", str(p1), str(p2), "-o", str(merged)])
    assert res.exit_code == 0
    assert merged.exists()


def test_cli_split_success(tmp_path: Path):
    from pdf_tool.adapters.image_to_pdf import ImageToPdfAdapter

    p1 = tmp_path / "sample.pdf"
    img1 = _make_png(tmp_path / "i1.png")
    adapter = ImageToPdfAdapter()
    adapter.convert(img1, p1)

    out_dir = tmp_path / "split_out"
    res = runner.invoke(app, ["split", str(p1), "--pages", "1", "-o", str(out_dir)])
    assert res.exit_code == 0
    assert out_dir.exists()


def test_cli_compress_success(tmp_path: Path):
    from pdf_tool.adapters.image_to_pdf import ImageToPdfAdapter

    p1 = tmp_path / "comp_in.pdf"
    img1 = _make_png(tmp_path / "comp_i.png")
    adapter = ImageToPdfAdapter()
    adapter.convert(img1, p1)

    comp_out = tmp_path / "comp_out.pdf"
    res = runner.invoke(app, ["compress", str(p1), "--level", "medium", "-o", str(comp_out)])
    assert res.exit_code == 0
    assert comp_out.exists()
