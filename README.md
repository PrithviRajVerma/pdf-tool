# 📄 pdf-tool

> **Universal document conversion and PDF manipulation CLI.**  
> Fast, modular, and dependency-aware. Convert, merge, split, compress, extract tables, OCR, and transform documents across formats directly from your terminal.

---

## ⚡ Quick Start

Install via `uv` or `pip`:

```bash
# Recommended: install as an isolated global tool with uv
uv tool install pdf-tool

# Or with pip
pip install pdf-tool
```

### Direct Mode (No Subcommand Required)

`pdf-tool` provides a lightning-fast direct CLI alias `pdf` that automatically figures out what you want to do based on file extensions:

```bash
pdf photo.jpg                    # → Converts to photo.pdf
pdf photo.jpg document.pdf        # → Converts photo.jpg to document.pdf
pdf img1.jpg img2.png out.pdf     # → Merges multiple images into out.pdf
pdf doc.pdf page.png             # → Extracts PDF pages to page-1.png, page-2.png, ...
```

---

## 🚀 Features & Commands

### 1. Universal Conversion (`pdf convert` / `pdf c`)

Convert between dozens of formats with automatic engine selection:

```bash
# Images ↔ PDF
pdf convert photo.jpg --to pdf
pdf convert doc.pdf --to png --dpi 300

# Office Documents → PDF (via headless LibreOffice)
pdf convert report.docx --to pdf
pdf convert presentation.pptx --to pdf
pdf convert budget.xlsx --to pdf

# Web & Markdown → PDF (via WeasyPrint, Pygments syntax highlighting, & Mermaid.js diagrams)
pdf convert README.md --to pdf                 # Visual vector flowcharts & code highlighting
pdf convert report.html --to pdf

# Reverse Conversions (PDF → Editable formats)
pdf convert scanned.pdf --to docx              # High-fidelity Word document reconstruction
pdf convert financial.pdf --to csv             # Extract detected tables to CSV
pdf convert balance_sheet.pdf --to xlsx        # Extract tables to multi-sheet Excel
pdf convert paper.pdf --to md                  # Structured Markdown (preserves headings, tables, code)
pdf convert paper.pdf --to txt                 # Plain text extraction
```

#### 📦 Batch Processing & Globbing

Convert entire directories of files sequentially or concurrently:

```bash
# Convert all DOCX files to PDF in batch
pdf convert "*.docx" --to pdf

# Concurrently convert files using multi-threading
pdf convert "docs/*.md" --to pdf --parallel --workers 4

# Save batch outputs to a target directory
pdf convert "*.jpg" --to pdf --batch --output-dir ./converted/
```

At the end of batch conversions, a summary table reports individual durations, output sizes, and status.

---

### 2. PDF Merge (`pdf merge` / `pdf m`)

Merge two or more PDFs into a single continuous document:

```bash
pdf merge chapter1.pdf chapter2.pdf chapter3.pdf -o complete_book.pdf
# Positional shortcut
pdf m a.pdf b.pdf combined.pdf
```

---

### 3. PDF Split (`pdf split` / `pdf s`)

Extract specific page ranges or divide into chunks:

```bash
# Extract specific pages (1-based, ranges and individual pages)
pdf split book.pdf --pages 1-5,10,12-15 -o ./chapters/

# Split into chunks of N pages
pdf split archive.pdf --every 10 -o ./chunks/

# Short positional argument syntax
pdf split book.pdf 1-5
pdf split archive.pdf 10
```

---

### 4. PDF Compress (`pdf compress` / `pdf z`)

Reduce PDF file size using Ghostscript with automatic fallback to `pypdf`:

```bash
pdf compress heavy.pdf --level high -o optimized.pdf
pdf compress report.pdf --level medium
```

Levels supported: `high`, `medium`, `low`.

---

### 5. OCR Scanned PDFs (`pdf ocr` / `pdf o`)

Add a searchable and selectable text layer to scanned PDFs using Tesseract OCR:

```bash
# Run OCR in English
pdf ocr scan.pdf -o searchable.pdf

# Specify language (e.g., German, French, Spanish)
pdf ocr scan.pdf --lang deu

# Force OCR on already processed files & deskew tilted scans
pdf ocr document.pdf --force --deskew
```

---

### 6. User Configuration (`pdf config` / `pdf cfg`)

Manage persistent defaults in `~/.pdf-tool/config.toml`:

```bash
# View active configuration and defaults
pdf config show

# Get a specific setting
pdf config get defaults.image_dpi

# Set preferred DPI and compression level
pdf config set defaults.image_dpi 200
pdf config set defaults.compression_level high
pdf config set defaults.ocr_language eng

# Reset settings to factory defaults
pdf config reset
pdf config reset --key defaults.image_dpi

# View path to config file
pdf config path
```

---

### 7. Dependency Diagnostics (`pdf doctor` / `pdf doc`)

Inspect which document engines and system binaries are available on your machine:

```bash
pdf doctor
```

Output:
```text
pdf-tool v0.1.0  |  Python 3.12.0

                             🩺 System Dependencies                             
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Adapter / Tool      ┃ Binary    ┃ Status              ┃ Install Command      ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ Ghostscript (PDF    │ gs        │ ✅ Found            │ sudo apt install     │
│ Compress)           │           │ /usr/bin/gs         │ ghostscript          │
│ LibreOffice         │ soffice   │ ✅ Found            │ sudo apt install     │
│ (DOCX/PPTX/XLSX →   │           │ /usr/bin/soffice    │ libreoffice          │
│ PDF)                │           │                     │                      │
│ Tesseract (OCR)     │ tesseract │ ✅ Found            │ sudo apt install     │
│                     │           │ /usr/bin/tesseract  │ tesseract-ocr        │
└─────────────────────┴───────────┴─────────────────────┴──────────────────────┘
               🐍 Pure-Python Adapters (no system deps required)                
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Adapter     ┃ Supports                                         ┃ Status      ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ Pillow      │ Image → PDF (JPG, PNG, WEBP, TIFF, HEIC)         │ ✅ Built-in │
│ PyMuPDF     │ PDF → Image, PDF validation                      │ ✅ Built-in │
│ WeasyPrint  │ Markdown (.md) & HTML → PDF                      │ ✅ Built-in │
│ pdf2docx    │ PDF → Word (.docx) layout reconstruction         │ ✅ Built-in │
│ pdfplumber  │ PDF → CSV & Excel table extraction               │ ✅ Built-in │
│ pymupdf4llm │ PDF → Structured Markdown & plain text           │ ✅ Built-in │
│ pypdf       │ Merge, Split                                     │ ✅ Built-in │
└─────────────┴──────────────────────────────────────────────────┴─────────────┘
```

---

## 🐳 Docker Usage

A pre-packaged multi-arch container image bundled with LibreOffice, Tesseract, Ghostscript, and Poppler is available:

```bash
# Pull the latest image
docker pull ghcr.io/example/pdf-tool:latest

# Run conversions by mounting the current directory
docker run --rm -v "$(pwd):/data" ghcr.io/example/pdf-tool convert report.docx --to pdf
docker run --rm -v "$(pwd):/data" ghcr.io/example/pdf-tool ocr scan.pdf -o searchable.pdf
docker run --rm -v "$(pwd):/data" ghcr.io/example/pdf-tool doctor
```

---

## 📋 Format Support Matrix

| Source Format | Target Format | Engine | System Dependency |
|:---|:---|:---|:---|
| JPG / PNG / WEBP / TIFF / HEIC | PDF | Pillow / pillow-heif | *None (Pure Python)* |
| PDF | PNG / JPG | PyMuPDF | *None (Pure Python)* |
| DOCX / PPTX / XLSX / ODT / RTF | PDF | LibreOffice (headless) | `soffice` (LibreOffice) |
| Markdown (`.md`) | PDF | WeasyPrint + Pygments | *None (Pure Python)* |
| HTML (`.html`) | PDF | WeasyPrint | *None (Pure Python)* |
| PDF | DOCX | pdf2docx | *None (Pure Python)* |
| PDF | CSV / XLSX | pdfplumber + openpyxl | *None (Pure Python)* |
| PDF | Markdown / TXT | pymupdf4llm | *None (Pure Python)* |
| PDF (Scanned) | PDF (Searchable) | ocrmypdf | `tesseract` |
| PDF (Multi-file) | PDF (Merged) | pypdf | *None (Pure Python)* |
| PDF | PDF (Chunks/Ranges) | pypdf | *None (Pure Python)* |
| PDF | PDF (Compressed) | Ghostscript + pypdf | `gs` (Optional for high) |

---

## 🛠️ Development & Contributing

See [CONTRIBUTING.md](file:///home/assassin/MY_WORK/Code/my-projects/pdf-converter/CONTRIBUTING.md) for detailed guidelines on adding new conversion adapters.

```bash
# Clone and setup with uv
git clone https://github.com/example/pdf-tool.git
cd pdf-tool
uv sync --all-extras --dev

# Run linters and tests
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=pdf_tool
```

## 📄 License

MIT License. See `LICENSE` for details.
