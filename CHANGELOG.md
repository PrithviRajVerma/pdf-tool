# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-28

### Added
- **Core CLI Infrastructure (Phase 1):**
  - Unified Typer command line interface with dual entry points: `pdf` and `pdf-tool`.
  - Direct conversion routing syntax without subcommand requirements: `pdf photo.jpg document.pdf`.
  - Adapter strategy registry for decoupled, pluggable document conversion engines.
  - Automatic MIME and extension detection via `python-magic` with fallback resolution.
  - System dependency detection with actionable, distro-specific install hints (`pdf doctor`).
  - Image to PDF conversion supporting JPG, PNG, WEBP, TIFF, BMP, and HEIC with EXIF auto-rotation.
  - PDF to image extraction with configurable DPI and page range extraction.
  - Multi-file PDF merging, page splitting (ranges and chunk intervals), and Ghostscript/pypdf compression.
- **Office & Web Formats (Phase 2):**
  - Headless LibreOffice conversion wrapper with isolated temporary user profiles supporting DOCX, PPTX, XLSX, ODT, RTF, and CSV.
  - Markdown to PDF conversion using `markdown-it-py` and WeasyPrint with Pygments syntax highlighting, clean typography, and A4 page layout controls.
  - Native Mermaid.js diagram and flowchart vector SVG rendering via `@mermaid-js/mermaid-cli` (`mmdc`) with transparent backgrounds and printable height constraints.
  - Thread-pool pre-compilation (`ThreadPoolExecutor`) for parallel rendering of multiple Mermaid diagram blocks in large markdown files.
  - Automatic syntax sanitization and retry recovery for common Mermaid edge-case quirks (such as unquoted parentheses in edge labels).
  - Local HTML to PDF conversion via WeasyPrint.
- **Reverse Conversions & OCR (Phase 3):**
  - PDF to Word (`.docx`) document structure reconstruction via `pdf2docx`.
  - PDF table extraction to CSV and multi-sheet Excel workbooks (`.xlsx`) via `pdfplumber` and `openpyxl`.
  - PDF to Markdown and plain text conversion preserving headings, tables, and lists via `pymupdf4llm`.
  - Scanned PDF OCR text-layer addition using `ocrmypdf` and Tesseract with `--lang`, `--force`, and `--deskew` options (`pdf ocr`).
- **Polish, Testing & Ship (Phase 4):**
  - Persistent user configuration manager backed by `~/.pdf-tool/config.toml` with `pdf config show/get/set/reset/path` commands.
  - Configuration default propagation across all CLI commands.
  - Batch conversion engine with glob wildcard pattern expansion (`pdf convert "*.docx" --to pdf`).
  - Concurrent multi-threaded batch processing using `concurrent.futures.ThreadPoolExecutor` (`--parallel`, `--workers`).
  - Rich batch summary table showing file-by-file duration, status, and output size metrics.
  - Multi-stage Docker container image bundling LibreOffice, Tesseract, Ghostscript, Poppler, and fonts.
  - GitHub Actions CI workflow covering Python 3.11, 3.12, 3.13, and 3.14 with Ruff linting and pytest coverage.
  - GitHub Container Registry (GHCR) multi-architecture release workflow.
  - Comprehensive test suite with 115 unit and integration tests achieving 85% code coverage.
