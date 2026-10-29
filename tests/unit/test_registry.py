"""Unit tests for ConversionRegistry."""

from __future__ import annotations

import pytest

from pdf_tool.exceptions import UnsupportedConversionError
from pdf_tool.router.registry import ConversionRegistry, registry


class TestConversionRegistry:
    def test_singleton(self) -> None:
        """Registry must be a singleton."""
        r1 = ConversionRegistry()
        r2 = ConversionRegistry()
        assert r1 is r2

    def test_register_and_lookup(self) -> None:
        """A registered adapter should be retrievable via lookup."""
        # Ensure adapters are loaded (they self-register on import)
        import pdf_tool.adapters  # noqa: F401

        adapter_cls = registry.lookup("jpeg", "pdf")
        assert adapter_cls is not None

    def test_lookup_jpg_alias(self) -> None:
        """'jpg' and 'jpeg' should both resolve to the ImageToPdfAdapter."""
        import pdf_tool.adapters  # noqa: F401
        from pdf_tool.adapters.image_to_pdf import ImageToPdfAdapter

        # jpeg → pdf
        cls_jpeg = registry.lookup("jpeg", "pdf")
        # jpg → pdf (also registered)
        cls_jpg = registry.lookup("jpg", "pdf")
        assert cls_jpeg is ImageToPdfAdapter
        assert cls_jpg is ImageToPdfAdapter

    def test_lookup_pdf_to_image(self) -> None:
        """PDF → png should resolve to PdfToImageAdapter."""
        import pdf_tool.adapters  # noqa: F401
        from pdf_tool.adapters.pdf_to_image import PdfToImageAdapter

        cls = registry.lookup("pdf", "png")
        assert cls is PdfToImageAdapter

    def test_unsupported_conversion_raises(self) -> None:
        """Lookup for an unregistered pair must raise UnsupportedConversionError."""
        with pytest.raises(UnsupportedConversionError):
            registry.lookup("docx", "xlsx")

    def test_list_supported_returns_pairs(self) -> None:
        """list_supported should return a non-empty list of (str, str) tuples."""
        import pdf_tool.adapters  # noqa: F401

        pairs = registry.list_supported()
        assert len(pairs) > 0
        for pair in pairs:
            assert isinstance(pair, tuple)
            assert len(pair) == 2

    def test_unsupported_error_attributes(self) -> None:
        """UnsupportedConversionError should store input/output format."""
        exc = UnsupportedConversionError("docx", "xlsx")
        assert exc.input_fmt == "docx"
        assert exc.output_fmt == "xlsx"
        assert "docx" in str(exc)
        assert "xlsx" in str(exc)
