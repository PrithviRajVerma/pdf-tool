"""OCR adapter using ocrmypdf and Tesseract."""

from __future__ import annotations

import time
from pathlib import Path

import ocrmypdf
import ocrmypdf.exceptions as oe

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError, MissingDependencyError
from pdf_tool.utils.dependency_checker import _INSTALL_HINTS, check


class OcrAdapter(BaseAdapter):
    """Adds a searchable text layer to scanned PDFs using ocrmypdf and Tesseract."""

    @property
    def required_system_deps(self) -> list[str]:
        return ["tesseract"]

    @property
    def engine_name(self) -> str:
        return "OCRmyPDF (Tesseract)"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Run OCR on input PDF and save searchable PDF to output_path.

        Args:
            input_path: Source PDF path.
            output_path: Target PDF path.
            **options:
                lang (str): Tesseract language code, e.g. "eng", "fra", "deu" (default: "eng").
                force (bool): Force OCR even if text already exists (default: False).
                deskew (bool): Deskew skewed scans before OCR (default: True).
                rotate_pages (bool): Auto-detect and fix page orientation (default: True).

        Returns:
            ConversionResult with timing and file size metadata.

        Raises:
            MissingDependencyError: If Tesseract is not installed on the system.
            InvalidInputError: If the input PDF is missing or corrupt.
            ConversionFailedError: If OCR processing fails.
        """
        start = time.monotonic()

        # Check for tesseract binary
        tess_status = check("tesseract")
        if not tess_status.found:
            hints = _INSTALL_HINTS.get("tesseract", {})
            raise MissingDependencyError(dep_name="tesseract", install_hints=hints)

        if not input_path.exists():
            raise InvalidInputError(f"File not found: '{input_path}'")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        lang = options.get("lang", "eng")
        force_ocr = bool(options.get("force", False))
        deskew = bool(options.get("deskew", True))
        rotate_pages = bool(options.get("rotate_pages", True))

        try:
            # If force is not set, use skip_text=True so existing text is preserved
            exit_code = ocrmypdf.ocr(
                input_file=input_path,
                output_file=output_path,
                language=[lang],
                force_ocr=force_ocr,
                skip_text=not force_ocr,
                deskew=deskew,
                rotate_pages=rotate_pages,
                progress_bar=False,
            )
            if exit_code != 0:
                raise ConversionFailedError(f"OCR failed with exit code: {exit_code}")

        except oe.PriorOcrFoundError as exc:
            raise ConversionFailedError(
                f"PDF '{input_path.name}' already contains searchable text. "
                "Use '--force' to re-run OCR over existing text."
            ) from exc
        except oe.MissingDependencyError as exc:
            hints = _INSTALL_HINTS.get("tesseract", {})
            raise MissingDependencyError(dep_name="tesseract", install_hints=hints) from exc
        except oe.InputFileError as exc:
            raise InvalidInputError(f"Invalid PDF input file: {exc}") from exc
        except Exception as exc:
            if isinstance(exc, (MissingDependencyError, InvalidInputError)):
                raise
            raise ConversionFailedError(f"OCR processing failed: {exc}") from exc

        return self._make_result(input_path, output_path, start)
