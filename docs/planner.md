# 🗺️ Project Planner — `pdf-tool` CLI

> [!NOTE]
> This file is the **single source of truth for project progress**. Update it as each task is completed. Phases are designed to deliver **usable, working software** at the end of each one.

---

## Overall Progress

```
Phase 1 — Core Foundation    [ ██████████ ] 100% ✅ Completed
Phase 2 — Office & Web       [ ██████████ ] 100% ✅ Completed
Phase 3 — Reverse & Extract  [ ██████████ ] 100% ✅ Completed
Phase 4 — Polish & Ship      [ ██████████ ] 100% ✅ Completed (Local Features Ready)
```

---

## Milestone Summary

| Phase | Deliverable | Target | Status |
| :--- | :--- | :--- | :--- |
| **Phase 1** | Working CLI: Image→PDF, PDF→Image, Merge, Split, Compress, `doctor` | — | ✅ Completed |
| **Phase 2** | DOCX/PPTX/XLSX→PDF, Markdown→PDF, HTML→PDF | — | ✅ Completed |
| **Phase 3** | PDF→DOCX, PDF→CSV/XLSX, PDF→Text/MD, OCR | — | ✅ Completed |
| **Phase 4** | Config, Batch Processing, Full Test Suite (85% cov), Dockerfile, Docs | — | ✅ Completed |

---

## Phase 1 — Core Foundation

> **Goal:** Set up the project scaffold and implement all **pure-Python conversions** that have zero system binary requirements. Deliver a working CLI that handles the most common image-to-PDF workflows and PDF utility operations.

**Status:** ✅ Completed

### 1.1 Project Scaffold

- [x] Initialize project with `uv init pdf-tool`
- [x] Set up `pyproject.toml` with metadata and entrypoint (`pdf-tool = "pdf_tool.main:app"`)
- [x] Create directory structure (`cli/`, `router/`, `adapters/`, `utils/`)
- [x] Set up `pytest` + `pytest-cov` for testing
- [x] Create `tests/fixtures/` with sample files (`.jpg`, `.png`, `.pdf`)
- [x] Set up `.gitignore`, `README.md` stub

### 1.2 Core Utilities

- [x] `utils/progress.py` — Rich progress bar and spinner wrappers
- [x] `utils/output_validator.py` — Verify output file exists, is non-zero size, is a valid PDF
- [x] `utils/dependency_checker.py` — `shutil.which()` based binary detection, returns `DependencyStatus`
- [x] `utils/config.py` — `ConfigManager` reading/writing `~/.pdf-tool/config.toml`
- [x] `exceptions.py` — Full typed exception hierarchy (`PdfToolError`, `MissingDependencyError`, etc.)

### 1.3 Router / Registry

- [x] `router/file_inspector.py` — MIME + extension detection using `python-magic`
- [x] `router/registry.py` — `@registry.register` decorator + `ConversionRegistry.lookup()` method

### 1.4 Base Adapter

- [x] `adapters/base.py` — Abstract `BaseAdapter` with `required_deps`, `convert()`, `ConversionResult`

### 1.5 Image ↔ PDF Adapters (Pillow)

- [x] `adapters/image_to_pdf.py` — JPG, PNG, WEBP, TIFF, BMP → PDF (single and multi-image merge)
  - [x] Auto-rotation from EXIF data
  - [x] HEIC/HEIF support via `pillow-heif`
- [x] `adapters/pdf_to_image.py` — PDF → JPG / PNG (all pages or specific range, configurable DPI)

### 1.6 PDF Utility Adapters (pypdf)

- [x] `adapters/merge.py` — Merge multiple PDFs into one
- [x] `adapters/split.py` — Split by page range (`1-3,5`) or every N pages
- [x] `adapters/compress.py` — Compress PDF (Ghostscript first, pypdf fallback)

### 1.7 CLI Commands

- [x] `main.py` — Typer app root, register all sub-commands
- [x] `cli/convert.py` — Auto-routing `convert` command (detects format, dispatches adapter)
- [x] `cli/merge.py` — `merge` command
- [x] `cli/split.py` — `split` command with `--pages` and `--every` options
- [x] `cli/compress.py` — `compress` command with `--level high|medium|low`
- [x] `cli/doctor.py` — System dependency diagnostic table

### 1.8 Phase 1 Tests

- [x] Unit tests for `FileInspector`
- [x] Unit tests for `ConversionRegistry`
- [x] Unit tests for `DependencyChecker`
- [x] Integration test: JPG → PDF → JPG round-trip
- [x] Integration test: Multi-image → merged PDF
- [x] Integration test: PDF merge, split, compress

---

## Phase 2 — Office & Web Formats

> **Goal:** Add support for the highest-demand conversion category — Office documents and web-based formats. Requires LibreOffice and WeasyPrint to be installed.

**Status:** ✅ Completed

### 2.1 LibreOffice Subprocess Handler

- [x] Create `utils/libreoffice.py` — A reusable subprocess wrapper for LibreOffice headless with timeout and error handling
- [x] Handle edge case: LibreOffice locks its `~/.config/libreoffice` during concurrent runs (use temp `--user-data-dir` per process)
- [x] Write unit tests mocking `subprocess.run`

### 2.2 Office → PDF Adapters

- [x] `adapters/office_to_pdf.py` — DOCX, DOC, ODT, RTF, XLSX, XLS, ODS, CSV, PPTX, PPT, ODP → PDF via LibreOffice

### 2.3 Markdown → PDF Adapter

- [x] `adapters/markdown_to_pdf.py`
  - [x] Convert Markdown to HTML using `markdown-it-py` with extensions: tables, fenced code, footnotes, strikethrough
  - [x] Apply a default CSS stylesheet for clean PDF typography
  - [x] Render HTML → PDF via WeasyPrint
  - [x] Syntax highlighting in code blocks via `pygments`

### 2.4 HTML → PDF Adapter

- [x] `adapters/html_to_pdf.py`
  - [x] Accept a local `.html` file
  - [x] WeasyPrint for local HTML

### 2.5 CLI Updates

- [x] Auto-detect `.md`, `.html`, `.docx`, `.xlsx`, `.pptx` and default direct conversion to PDF
- [x] Update `doctor` to check for LibreOffice with Arch, Ubuntu, and macOS install commands

### 2.6 Phase 2 Tests

- [x] Unit tests for `run_libreoffice_convert` (timeout, missing binary, exit codes, output resolution)
- [x] Integration test: Office formats registered in registry and converted via LibreOffice handler
- [x] Integration test: Markdown → PDF (with tables, code blocks, headings)
- [x] Integration test: HTML file → PDF

---

## Phase 3 — Reverse Conversions & OCR

> **Goal:** Add reverse conversion capabilities (PDF back to editable formats) and OCR support for scanned documents.

**Status:** ✅ Completed

### 3.1 PDF → DOCX

- [x] `adapters/pdf_to_docx.py` — Using `pdf2docx`
  - [x] Handle multi-column layouts
  - [x] Handle scanned-PDF check (advise user to run OCR first)

### 3.2 PDF → Spreadsheet

- [x] `adapters/pdf_to_csv.py` — Using `pdfplumber` and `openpyxl` for table extraction
  - [x] Auto-detect tables in the PDF
  - [x] Export to CSV and multi-sheet Excel (.xlsx) workbooks
  - [x] Support `--page N` and `--table-index N` options

### 3.3 PDF → Text / Markdown

- [x] `adapters/pdf_to_text.py` — Using `pymupdf4llm`
  - [x] Output `.txt` or `.md` based on the output extension
  - [x] Preserve heading hierarchy, tables, lists, and code blocks
  - [x] Handle page ranges and multi-column layouts

### 3.4 OCR Adapter

- [x] `adapters/ocr.py` — Using `ocrmypdf`
  - [x] Add invisible text layer to scanned PDFs
  - [x] Support `--lang` option (e.g., `eng`, `deu`, `fra`, `hin`)
  - [x] Support `--force-ocr` to re-OCR already-text PDFs

### 3.5 CLI Updates

- [x] Expose `pdf ocr` top-level command and `pdf o` alias
- [x] Add `--pages`, `--page`, and `--table-index` options to `convert` command
- [x] Update `doctor` to check for `tesseract` binary and Phase 3 adapters

### 3.6 Phase 3 Tests

- [x] Integration test: Text PDF → DOCX (verify document structure and validity)
- [x] Integration test: PDF with table → CSV and XLSX (verify row/column extraction)
- [x] Integration test: PDF → Markdown and plain text (verify heading and content preservation)
- [x] Unit tests: OCR adapter dependency verification, error handling, and CLI command execution

---

## Phase 4 — Polish, Testing & Ship

> **Goal:** Make the project production-ready for public distribution. Full test coverage, Docker image, PyPI release, and polished documentation.

**Status:** ✅ Completed

### 4.1 Configuration

- [x] Implement `ConfigManager` fully (read/write `~/.pdf-tool/config.toml`)
- [x] Add `pdf-tool config set <key> <value>` and `pdf-tool config show` commands
- [x] Propagate user config defaults to all CLI commands

### 4.2 Batch Processing

- [x] Support glob patterns in `convert`: `pdf-tool convert *.docx --to pdf`
- [x] `--parallel` flag for batch conversions using `concurrent.futures`
- [x] Batch summary table at the end (files processed, successes, failures, total time)

### 4.3 Full Test Suite

- [x] Achieve ≥ 80% code coverage (85% coverage across 115 tests)
- [x] Add edge case tests: empty file, corrupt PDF, unsupported format error messages
- [x] Add tests for all CLI commands using `typer.testing.CliRunner`
- [x] Set up GitHub Actions CI: lint (Ruff), type-check (mypy), test (pytest) on push

### 4.4 Docker Image

- [x] Write multi-stage `Dockerfile` (build stage + slim runtime stage)
- [x] Install: LibreOffice, Tesseract (+ eng language pack), Ghostscript, Poppler utils
- [x] Publish to GitHub Container Registry (GHCR) via GitHub Actions on tag
- [x] Build multi-arch: `linux/amd64` + `linux/arm64`
- [x] Document Docker usage in README

### 4.5 PyPI Release Readiness

- [x] Finalize `pyproject.toml` classifiers, keywords, URLs, licensing
- [x] Write full `README.md` with install instructions, usage examples, format matrix
- [x] Offline build verified: `uv build --offline` builds wheel & sdist cleanly
- [x] Tag `v0.1.0` release notes in CHANGELOG.md

### 4.6 Developer Documentation

- [x] Finalize `docs/architecture.md`
- [x] Finalize `docs/decisions.md` (ADR-012, ADR-013, ADR-014)
- [x] `CONTRIBUTING.md`: How to add a new adapter (step-by-step)
- [x] `CHANGELOG.md`: Seed with v0.1.0 entries

---

## Backlog / Future Phases

> Items not in scope for v1.0 but worth tracking for future consideration.

- [ ] **TUI Mode:** An interactive terminal UI (using `textual`) for users who prefer a guided flow over remembering commands.
- [ ] **Watch Mode:** `pdf-tool watch ./inbox --to pdf` — auto-convert files dropped into a directory.
- [ ] **Plugin System:** Allow third-party adapters to register via `importlib.metadata` entry points.
- [ ] **GUI Wrapper:** A minimal desktop GUI (using `PyWebView` or `Tkinter`) wrapping the CLI for non-technical users.
- [ ] **Cloud Destinations:** `--output s3://bucket/key`, `--output gdrive://folder/` post-conversion upload.
- [ ] **Homebrew Formula:** Official formula that installs `pdf-tool` + all system deps in one command.
- [ ] **Windows MSI Installer:** Bundle Python + all deps into a self-contained installer.
- [ ] **More OCR Languages:** Auto-download Tesseract language packs via `pdf-tool ocr --install-lang fra`.

---

## Progress Update Log

> Append a dated entry here whenever a phase or major task is completed.

| Date | Update |
| :--- | :--- |
| 2026-10-27 | Project initialized. Architecture, decisions, and planner docs created. Ready to begin Phase 1. |
| 2026-10-27 | Phase 1 completed: Scaffolding, Typer CLI commands (convert, merge, split, compress, doctor), Adapters (ImageToPdf, PdfToImage, Merge, Split, Compress), FileInspector, Registry, and full test suite passing (45/45 tests). |
| 2026-10-27 | Phase 2 completed: Added WeasyPrint and Pygments dependencies. Implemented MarkdownToPdfAdapter (typography, Pygments code syntax highlighting, table formatting), HtmlToPdfAdapter, OfficeToPdfAdapter (LibreOffice headless wrapper with isolated user profile), and auto-detection for document types. All 68/68 tests passing. |
| 2026-10-28 | Phase 3 completed: Added pdf2docx, pdfplumber, openpyxl, and ocrmypdf dependencies. Implemented PdfToDocxAdapter, PdfToCsvAdapter (CSV & multi-sheet Excel), PdfToTextAdapter (structured Markdown & plain text via pymupdf4llm), and OcrAdapter with dedicated `pdf ocr` command / `pdf o` alias. Full test suite passing (79/79 tests). |
| 2026-10-29 | Phase 4 completed: Implemented persistent ConfigManager (`pdf config`), batch conversion with globbing and parallel ThreadPoolExecutor, edge-case hardening, full test suite (115 tests passing, 85% coverage), Docker multi-stage build, CI workflows, and complete documentation. All features verified up and running locally. |
