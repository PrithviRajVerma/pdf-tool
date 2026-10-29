"""Integration tests for PDF merge, split, and compress."""

from __future__ import annotations

import warnings
from pathlib import Path

import pymupdf as fitz

from pdf_tool.adapters.compress import CompressAdapter
from pdf_tool.adapters.merge import MergeAdapter
from pdf_tool.adapters.split import SplitAdapter
from pdf_tool.utils.output_validator import validate_pdf


def _make_pdf(path: Path, num_pages: int = 1, text_prefix: str = "Page") -> Path:
    """Create a minimal PDF with *num_pages* pages using PyMuPDF."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=200, height=200)
        page.insert_text((10, 50), f"{text_prefix} {i + 1}")
    doc.save(str(path))
    doc.close()
    return path


class TestMerge:
    def test_merge_two_pdfs(self, tmp_path: Path) -> None:
        """Two single-page PDFs should merge into a 2-page PDF."""
        pdf1 = _make_pdf(tmp_path / "a.pdf", num_pages=1, text_prefix="Doc A Page")
        pdf2 = _make_pdf(tmp_path / "b.pdf", num_pages=1, text_prefix="Doc B Page")
        out = tmp_path / "merged.pdf"

        adapter = MergeAdapter()
        result = adapter.merge([pdf1, pdf2], out)

        assert result.output_path.exists()
        validate_pdf(result.output_path)

        doc = fitz.open(str(result.output_path))
        assert doc.page_count == 2
        doc.close()

    def test_merge_three_multipage_pdfs(self, tmp_path: Path) -> None:
        """Three 2-page PDFs should merge into a 6-page PDF."""
        pdfs = [_make_pdf(tmp_path / f"doc{i}.pdf", num_pages=2) for i in range(3)]
        out = tmp_path / "merged.pdf"

        adapter = MergeAdapter()
        result = adapter.merge(pdfs, out)

        doc = fitz.open(str(result.output_path))
        assert doc.page_count == 6
        doc.close()

    def test_merge_result_metadata(self, tmp_path: Path) -> None:
        pdf1 = _make_pdf(tmp_path / "a.pdf")
        pdf2 = _make_pdf(tmp_path / "b.pdf")
        out = tmp_path / "merged.pdf"

        adapter = MergeAdapter()
        result = adapter.merge([pdf1, pdf2], out)

        assert result.engine == "pypdf"
        assert result.output_size_bytes > 0
        assert result.duration_seconds >= 0


class TestSplit:
    def test_split_by_page_range(self, tmp_path: Path) -> None:
        """Splitting pages 1-2 from a 4-page PDF should produce one 2-page PDF."""
        pdf = _make_pdf(tmp_path / "four_pages.pdf", num_pages=4)
        out_dir = tmp_path / "split_out"

        adapter = SplitAdapter()
        outputs = adapter.split(pdf, out_dir, page_range="1-2")

        assert len(outputs) == 1
        out = outputs[0]
        assert out.exists()
        validate_pdf(out)

        doc = fitz.open(str(out))
        assert doc.page_count == 2
        doc.close()

    def test_split_by_every_n_pages(self, tmp_path: Path) -> None:
        """Splitting a 6-page PDF every 2 pages should produce 3 PDFs."""
        pdf = _make_pdf(tmp_path / "six_pages.pdf", num_pages=6)
        out_dir = tmp_path / "chunks"

        adapter = SplitAdapter()
        outputs = adapter.split(pdf, out_dir, every=2)

        assert len(outputs) == 3
        for out in outputs:
            assert out.exists()
            doc = fitz.open(str(out))
            assert doc.page_count == 2
            doc.close()

    def test_split_single_page_per_file(self, tmp_path: Path) -> None:
        """Default split (no args) should produce one file per page."""
        pdf = _make_pdf(tmp_path / "three.pdf", num_pages=3)
        out_dir = tmp_path / "pages"

        adapter = SplitAdapter()
        outputs = adapter.split(pdf, out_dir)

        assert len(outputs) == 3
        for out in outputs:
            doc = fitz.open(str(out))
            assert doc.page_count == 1
            doc.close()

    def test_split_comma_page_range(self, tmp_path: Path) -> None:
        """Non-contiguous page range '1,3' from a 4-page PDF."""
        pdf = _make_pdf(tmp_path / "four.pdf", num_pages=4)
        out_dir = tmp_path / "out"

        adapter = SplitAdapter()
        outputs = adapter.split(pdf, out_dir, page_range="1,3")

        assert len(outputs) == 1
        doc = fitz.open(str(outputs[0]))
        assert doc.page_count == 2
        doc.close()


class TestCompress:
    def test_compress_output_exists(self, tmp_path: Path) -> None:
        """Compress should produce a valid output PDF."""
        pdf = _make_pdf(tmp_path / "source.pdf", num_pages=2)
        out = tmp_path / "compressed.pdf"

        adapter = CompressAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Suppress gs-not-found warning
            result = adapter.compress(pdf, out, level="medium")

        assert result.output_path.exists()
        validate_pdf(result.output_path)

    def test_compress_output_size_reasonable(self, tmp_path: Path) -> None:
        """Output should be non-zero and ideally ≤ input size (for real content)."""
        pdf = _make_pdf(tmp_path / "source.pdf", num_pages=3)
        out = tmp_path / "compressed.pdf"
        input_size = pdf.stat().st_size
        assert input_size > 0

        adapter = CompressAdapter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = adapter.compress(pdf, out, level="high")

        assert result.output_size_bytes > 0
        # For synthetic PDFs compression ratio varies, just check non-zero
        # (pypdf fallback may not reduce size for tiny PDFs)

    def test_compress_all_levels(self, tmp_path: Path) -> None:
        """All three compression levels should produce valid output."""
        for level in ("high", "medium", "low"):
            pdf = _make_pdf(tmp_path / f"src_{level}.pdf")
            out = tmp_path / f"compressed_{level}.pdf"

            adapter = CompressAdapter()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = adapter.compress(pdf, out, level=level)

            assert result.output_path.exists()
            validate_pdf(result.output_path)
