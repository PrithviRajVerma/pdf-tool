"""HTML to PDF conversion adapter using WeasyPrint."""

from __future__ import annotations

import time
from pathlib import Path

import weasyprint

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry


@registry.register(input_fmts=["html", "htm"], output_fmt="pdf")
class HtmlToPdfAdapter(BaseAdapter):
    """Converts HTML files to PDF using WeasyPrint."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "WeasyPrint"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert an HTML document to PDF.

        Args:
            input_path: Path to the local .html file.
            output_path: Target .pdf path.
            **options:
                stylesheets (list[str] | None): Optional list of CSS file paths.

        Returns:
            ConversionResult with metadata.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"HTML file not found: '{input_path}'")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        stylesheets = options.get("stylesheets", None)

        try:
            doc = weasyprint.HTML(
                filename=str(input_path),
                base_url=str(input_path.parent),
            )
            doc.write_pdf(target=str(output_path), stylesheets=stylesheets)
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to render PDF from HTML '{input_path.name}': {exc}"
            ) from exc

        return self._make_result(input_path, output_path, start)
