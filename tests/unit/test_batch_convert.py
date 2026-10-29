"""Unit tests for batch conversion and glob handling."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer
from PIL import Image

from pdf_tool.cli.convert import (
    _convert_single_item,
    _expand_inputs,
    convert,
)


def _make_png(path: Path) -> Path:
    img = Image.new("RGB", (50, 50), color=(100, 150, 200))
    img.save(str(path), format="PNG")
    return path


def test_expand_inputs_exact_and_glob(tmp_path: Path):
    f1 = tmp_path / "a.md"
    f2 = tmp_path / "b.md"
    f3 = tmp_path / "c.txt"
    f1.write_text("# Doc A")
    f2.write_text("# Doc B")
    f3.write_text("Text C")

    # Exact paths
    exact = _expand_inputs([f1, f2])
    assert exact == [f1, f2]

    # Glob pattern
    globbed = _expand_inputs([tmp_path / "*.md"])
    assert len(globbed) == 2
    assert f1 in globbed
    assert f2 in globbed
    assert f3 not in globbed


def test_convert_single_item(tmp_path: Path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Sample Header\nSome content.")

    res = _convert_single_item(
        input_path=md_file,
        target_dir=tmp_path / "out",
        target_fmt="pdf",
        options={},
    )
    assert res.success is True
    assert res.output_file is not None
    assert res.output_file.exists()
    assert res.output_file.suffix == ".pdf"


def test_convert_single_item_nonexistent():
    res = _convert_single_item(
        input_path=Path("/nonexistent/file.md"),
        target_dir=None,
        target_fmt="pdf",
        options={},
    )
    assert res.success is False
    assert "File not found" in str(res.error_message)


def test_batch_convert_multiple_markdown_sequential(tmp_path: Path):
    m1 = tmp_path / "doc1.md"
    m2 = tmp_path / "doc2.md"
    m1.write_text("# First Document")
    m2.write_text("# Second Document")
    out_dir = tmp_path / "output_seq"

    convert(
        input_files=[m1, m2],
        to="pdf",
        output_dir=out_dir,
        parallel=False,
    )

    assert (out_dir / "doc1.pdf").exists()
    assert (out_dir / "doc2.pdf").exists()


def test_batch_convert_multiple_markdown_parallel(tmp_path: Path):
    m1 = tmp_path / "p1.md"
    m2 = tmp_path / "p2.md"
    m3 = tmp_path / "p3.md"
    m1.write_text("# P1")
    m2.write_text("# P2")
    m3.write_text("# P3")
    out_dir = tmp_path / "output_par"

    convert(
        input_files=[m1, m2, m3],
        to="pdf",
        output_dir=out_dir,
        parallel=True,
        workers=2,
    )

    assert (out_dir / "p1.pdf").exists()
    assert (out_dir / "p2.pdf").exists()
    assert (out_dir / "p3.pdf").exists()


def test_batch_convert_images_with_batch_flag(tmp_path: Path):
    img1 = _make_png(tmp_path / "img1.png")
    img2 = _make_png(tmp_path / "img2.png")
    out_dir = tmp_path / "out_img_batch"

    # --batch ensures separate PDFs instead of merging into one
    convert(
        input_files=[img1, img2],
        to="pdf",
        output_dir=out_dir,
        batch=True,
        parallel=False,
    )

    assert (out_dir / "img1.pdf").exists()
    assert (out_dir / "img2.pdf").exists()


def test_batch_convert_partial_failure(tmp_path: Path):
    good = tmp_path / "good.md"
    good.write_text("# Good Doc")
    bad = tmp_path / "bad.unknown_ext_xyz"
    bad.write_text("weird data")

    with pytest.raises(typer.Exit) as exc:
        convert(
            input_files=[good, bad],
            to="pdf",
            parallel=False,
        )
    assert exc.value.exit_code == 1
    assert (tmp_path / "good.pdf").exists()
