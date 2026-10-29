"""PDF to CSV / Excel spreadsheet adapter using pdfplumber."""

from __future__ import annotations

import csv
import time
from pathlib import Path

import openpyxl
import pdfplumber

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry


@registry.register(input_fmts=["pdf"], output_fmt="csv")
@registry.register(input_fmts=["pdf"], output_fmt="xlsx")
class PdfToCsvAdapter(BaseAdapter):
    """Extracts tables from PDF files into CSV or Excel (.xlsx) spreadsheets."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "pdfplumber"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Extract tables from PDF into CSV or XLSX.

        Args:
            input_path: Source PDF path.
            output_path: Target .csv or .xlsx path.
            **options:
                page (int | None): 1-based specific page number to extract from.
                table_index (int | None): 1-based specific table index to extract.

        Returns:
            ConversionResult with metadata.

        Raises:
            InvalidInputError: If the PDF cannot be opened.
            ConversionFailedError: If extraction fails or no tables are found.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"File not found: '{input_path}'")

        target_page = options.get("page")
        table_idx = options.get("table_index")

        try:
            with pdfplumber.open(str(input_path)) as pdf:
                total_pages = len(pdf.pages)
                if total_pages == 0:
                    raise InvalidInputError(f"PDF '{input_path.name}' has no pages.")

                pages_to_process = (
                    [pdf.pages[target_page - 1]]
                    if target_page and 1 <= target_page <= total_pages
                    else pdf.pages
                )

                all_tables: list[tuple[int, list[list[str]]]] = []

                for page_num, p in enumerate(pages_to_process, start=1):
                    # Try default strategy first (lines/rects)
                    extracted = p.extract_tables()

                    # Fallback to text-based alignment strategy if no tables found
                    if not extracted:
                        extracted = p.extract_tables(
                            {
                                "vertical_strategy": "text",
                                "horizontal_strategy": "text",
                                "snap_y_tolerance": 4,
                            }
                        )

                    for t in extracted:
                        cleaned_table = [
                            [(cell.replace("\n", " ").strip() if cell else "") for cell in row]
                            for row in t
                            if any(cell and str(cell).strip() for cell in row)
                        ]
                        if cleaned_table:
                            all_tables.append((page_num, cleaned_table))

        except Exception as exc:
            if isinstance(exc, InvalidInputError):
                raise
            raise ConversionFailedError(f"Failed to read PDF tables: {exc}") from exc

        if not all_tables:
            raise ConversionFailedError(
                f"No tabular data could be extracted from '{input_path.name}'. "
                "The PDF might contain scanned images without text, or non-tabular layout."
            )

        if table_idx is not None and 1 <= table_idx <= len(all_tables):
            all_tables = [all_tables[table_idx - 1]]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        is_xlsx = output_path.suffix.lower() == ".xlsx"

        try:
            if is_xlsx:
                self._write_xlsx(all_tables, output_path)
            else:
                self._write_csv(all_tables, output_path)
        except Exception as exc:
            raise ConversionFailedError(f"Failed to write spreadsheet: {exc}") from exc

        return self._make_result(input_path, output_path, start)

    def _write_csv(
        self,
        tables: list[tuple[int, list[list[str]]]],
        output_path: Path,
    ) -> None:
        """Write extracted tables into a CSV file."""
        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            for idx, (page_num, table) in enumerate(tables):
                if len(tables) > 1:
                    writer.writerow([f"# Table {idx + 1} (Page {page_num})"])
                for row in table:
                    writer.writerow(row)
                if idx < len(tables) - 1:
                    writer.writerow([])  # blank line separator between tables

    def _write_xlsx(
        self,
        tables: list[tuple[int, list[list[str]]]],
        output_path: Path,
    ) -> None:
        """Write extracted tables into an Excel workbook."""
        wb = openpyxl.Workbook()
        # Remove default active sheet
        wb.remove(wb.active)

        for idx, (page_num, table) in enumerate(tables):
            sheet_title = f"Table {idx + 1} (P{page_num})"[:31]  # Excel 31-char sheet limit
            ws = wb.create_sheet(title=sheet_title)
            for row in table:
                ws.append(row)

        wb.save(str(output_path))
