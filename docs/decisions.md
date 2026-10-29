# 📋 Decision Log — `pdf-tool` CLI

> [!NOTE]
> This file logs **Architecture Decision Records (ADRs)** — every critical design or technology choice made during the project, along with the reasoning and alternatives that were considered. Update this file **as implementation happens**, not after the fact.

---

## ADR Format

Each decision follows this template:

```
### ADR-XXX: <Short Title>
- **Date:** YYYY-MM-DD
- **Status:** Proposed | Accepted | Deprecated | Superseded by ADR-XXX
- **Decider:** <who made this decision>
```

---

## Decision Index

| ID | Title | Status | Date |
| :--- | :--- | :--- | :--- |
| [ADR-001](#adr-001-python-as-primary-language) | Python as Primary Language | ✅ Accepted | 2026-10-27 |
| [ADR-002](#adr-002-typer--rich-for-cli-framework) | Typer + Rich for CLI Framework | ✅ Accepted | 2026-10-27 |
| [ADR-003](#adr-003-adapter-strategy-pattern-for-conversion-routing) | Adapter / Strategy Pattern for Conversion Routing | ✅ Accepted | 2026-10-27 |
| [ADR-004](#adr-004-delegate-office-formats-to-libreoffice-headless) | Delegate Office Formats to LibreOffice Headless | ✅ Accepted | 2026-10-27 |
| [ADR-005](#adr-005-pymupdf-as-primary-pdf-manipulation-library) | PyMuPDF as Primary PDF Manipulation Library | ✅ Accepted | 2026-10-27 |
| [ADR-006](#adr-006-weasyprint-as-primary-htmlmarkdown-to-pdf-renderer) | WeasyPrint as Primary HTML/Markdown-to-PDF Renderer | ✅ Accepted | 2026-10-27 |
| [ADR-007](#adr-007-uv-for-dependency-management--packaging) | UV for Dependency Management & Packaging | ✅ Accepted | 2026-10-27 |
| [ADR-008](#adr-008-lazy-per-adapter-dependency-checking) | Lazy Per-Adapter Dependency Checking | ✅ Accepted | 2026-10-27 |
| [ADR-009](#adr-009-typed-exception-hierarchy) | Typed Exception Hierarchy | ✅ Accepted | 2026-10-27 |
| [ADR-010](#adr-010-docker-as-a-first-class-distribution-target) | Docker as First-Class Distribution Target | ✅ Accepted | 2026-10-27 |
| [ADR-011](#adr-011-short-tool-name-pdf-and-direct-conversion-ux) | Short Tool Name `pdf` and Direct Conversion UX | ✅ Accepted | 2026-10-27 |
| [ADR-012](#adr-012-centralized-user-configuration-with-dot-notation-toml) | Centralized User Configuration with Dot-Notation TOML | ✅ Accepted | 2026-10-28 |
| [ADR-013](#adr-013-batch-processing-engine-and-concurrency-model) | Batch Processing Engine and Concurrency Model | ✅ Accepted | 2026-10-28 |
| [ADR-014](#adr-014-multi-stage-containerization-with-headless-engines) | Multi-Stage Containerization with Headless Engines | ✅ Accepted | 2026-10-28 |

---

## ADR-001: Python as Primary Language

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
The tool needs to integrate with a large number of document processing libraries. The choice of language determines what libraries are directly available, how subprocess orchestration works, and how easy distribution is.

### Decision
Use **Python 3.11+** as the implementation language.

### Reasons
- The document processing ecosystem in Python (PyMuPDF, pdfplumber, pdf2docx, Pillow, WeasyPrint, ocrmypdf) is unmatched in any other language.
- Subprocess orchestration of system binaries (LibreOffice, Ghostscript, Tesseract) is trivial in Python.
- Wide developer familiarity → easier for contributors.
- `pipx` and `uv` provide clean, isolated distribution without requiring Docker.

### Alternatives Considered
| Language | Reason Rejected |
| :--- | :--- |
| **Go** | No mature document library ecosystem. Would require shelling out to system binaries for almost everything, with no benefit over Python for this use case. |
| **Rust** | Same problem as Go. Extremely strong for performance-critical systems, but the bottleneck here is LibreOffice/Tesseract subprocess time, not Python overhead. |
| **Node.js** | `pdf-lib`, `puppeteer` cover some cases but LibreOffice integration is fragile. Less mature for DOCX/XLSX extraction. |

---

## ADR-002: Typer + Rich for CLI Framework

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
The CLI needs clean argument parsing, auto-generated `--help`, shell autocompletion, and a polished terminal UX (progress bars, colored output, structured tables).

### Decision
Use **Typer** for command/argument declaration and **Rich** for all terminal output rendering.

### Reasons
- **Typer** is built on `click` (industry standard) but adds Python type hints as the source of truth for argument definitions — no boilerplate annotation dictionaries.
- Automatic `--help` text generation from docstrings.
- Built-in shell completion (bash, zsh, fish) via `--install-completion`.
- **Rich** is the de facto standard for beautiful terminal output in Python. Provides progress bars, spinners, panels, tables, and syntax highlighting.
- The two libraries are designed to work together.

### Alternatives Considered
| Library | Reason Rejected |
| :--- | :--- |
| **Click** | Typer is a superset of Click with less boilerplate. No reason to use Click directly. |
| **argparse** | Verbose, no autocompletion, no built-in UX niceties. |
| **Fire** | Too implicit; poor control over help text and argument validation. |

---

## ADR-003: Adapter / Strategy Pattern for Conversion Routing

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
There are ~20 distinct conversion paths, each requiring a different library or system binary. The architecture must allow adding new conversions without modifying existing code.

### Decision
Use the **Strategy / Adapter pattern** with a **central registry**. Each conversion type is an isolated class implementing `BaseAdapter`. Adapters self-register via a decorator. The router looks up the correct adapter by `(input_fmt, output_fmt)` key.

### Reasons
- **Open/Closed Principle:** Adding a new conversion = adding a new file. No existing code changes.
- Adapters are independently testable with mock engines.
- The registry provides a single source of truth for supported conversion pairs.
- Each adapter independently declares its `required_deps`, enabling precise dependency checking.

### Alternatives Considered
| Approach | Reason Rejected |
| :--- | :--- |
| **Giant if/elif chain in the router** | Unscalable. Every new format requires modifying the router. High merge conflict surface. |
| **Plugin system (importlib.metadata)** | Overly complex for the initial scope. May be introduced later for third-party adapter extensions. |

---

## ADR-004: Delegate Office Formats to LibreOffice Headless

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
DOCX, XLSX, PPTX, ODT, RTF → PDF conversions require faithful rendering of fonts, styles, tables, images, and complex layouts. Several Python-native alternatives exist.

### Decision
Use **LibreOffice in headless mode** (`soffice --headless --convert-to pdf`) via `subprocess` for all Office format → PDF conversions.

### Reasons
- **Best fidelity** for complex documents: LibreOffice's rendering engine handles embedded fonts, complex tables, chart objects, and page headers/footers better than any pure Python library.
- Already used by dozens of production document systems (e.g., Nextcloud, Collabora).
- Handles the entire MS Office format family as well as OpenDocument formats with a single engine.
- Free and open source.

### Alternatives Considered
| Library | Reason Rejected |
| :--- | :--- |
| **python-docx → reportlab** | `python-docx` can read DOCX structure but cannot render it to PDF natively. Mapping to reportlab is an enormous, fragile undertaking with poor table/image support. |
| **docx2pdf** | It uses LibreOffice or MS Word under the hood anyway. Adds an unnecessary wrapper with less control. |
| **MS Word COM automation** | Windows only. Unacceptable for a cross-platform CLI. |
| **Pandoc** | Good for simple/text-heavy documents but loses fidelity on complex formatting (tables, columns, images). |

### Trade-off Accepted
LibreOffice is a large binary (~300MB installed). This is a known friction point for users. Mitigated by the `pdf-tool doctor` command and the Docker image that ships with LibreOffice pre-installed.

---

## ADR-005: PyMuPDF as Primary PDF Manipulation Library

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
Several features require reading, rasterizing, and extracting content from PDFs: PDF → Image, PDF → Text, Output Validation, page count checks.

### Decision
Use **PyMuPDF (`import fitz`)** as the primary Python-level PDF engine for reading, rasterizing (PDF→Image), and text extraction.

### Reasons
- Fastest PDF rasterization in the Python ecosystem (benchmarks vs `pdf2image`/Poppler show 3-5x speedup).
- Excellent text extraction with structure (blocks, lines, words, tables).
- Small footprint — no external binary dependency (MuPDF is bundled in the wheel).
- Active development by Artifex, the company behind Ghostscript.
- `pymupdf4llm` (a sibling project) provides structured Markdown/text extraction needed for PDF → MD.

### Alternatives Considered
| Library | Reason Rejected |
| :--- | :--- |
| **pdfminer.six** | Text extraction only. Cannot rasterize. Slower than PyMuPDF. |
| **Poppler/pdf2image** | External binary dependency. Slower rasterization. PyMuPDF is a strict superset. |
| **pypdf** | Excellent for page manipulation (merge/split) but not designed for rasterization or content extraction. Used alongside PyMuPDF for merge/split operations. |

---

## ADR-006: WeasyPrint as Primary HTML/Markdown-to-PDF Renderer

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
Markdown and HTML → PDF conversions need CSS support (code block styling, tables, math), a clean Python API, and ideally no Chromium dependency.

### Decision
Use **WeasyPrint** as the primary renderer with **Playwright (Chromium)** as an optional fallback for users who need pixel-perfect output.

### Reasons
- WeasyPrint is a pure Python HTML/CSS → PDF engine that supports CSS Paged Media standard (proper page breaks, headers, footers).
- No external binary dependency (unlike Puppeteer/Playwright which download a Chromium build).
- Handles Markdown by first converting to HTML via `markdown-it-py` with extensions (tables, fenced code, footnotes).
- Produces standards-compliant PDF output.

### Trade-off Accepted
WeasyPrint does not support JavaScript. Complex JS-rendered pages will not render correctly. For those cases, users can opt into `--renderer playwright`.

---

## ADR-007: UV for Dependency Management & Packaging

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
The project needs a reproducible, fast build and dependency management system that also handles packaging for PyPI distribution.

### Decision
Use **UV** (by Astral, the makers of Ruff) for all package management: `uv sync`, `uv build`, `uv publish`.

### Reasons
- 10-100x faster than pip/venv for environment setup.
- Replaces `pip` + `venv` + `pip-tools` + `twine` with a single tool.
- Lock file (`uv.lock`) ensures 100% reproducible builds.
- `pyproject.toml`-native — no `setup.py` or `requirements.txt` sprawl.
- Built-in support for `[project.scripts]` to declare the `pdf-tool` entrypoint.

### Alternatives Considered
| Tool | Reason Rejected |
| :--- | :--- |
| **Poetry** | Slower resolver. UV is a strict superset in functionality for this use case. |
| **pip + venv** | No lock file. No build/publish tooling. Too many tools to chain manually. |
| **PDM** | Less community adoption than UV. UV is the clear emerging standard. |

---

## ADR-008: Lazy Per-Adapter Dependency Checking

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
The tool has many adapters with different system binary requirements. Checking all dependencies at startup would be slow and confusing (failing on a missing LibreOffice even when the user just wants to split a PDF).

### Decision
Dependency checks are **lazy** — only performed for the adapter that is actually needed for the requested conversion. The dedicated `pdf-tool doctor` command performs a full system-wide diagnostic.

### Reasons
- Users should not be blocked by unrelated missing dependencies.
- Startup time remains fast.
- `pdf-tool doctor` provides the full picture when the user wants to set up their system.

---

## ADR-009: Typed Exception Hierarchy

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
Errors can occur at many levels: missing deps, unsupported formats, engine crashes, corrupt input. The CLI must present clean, actionable error messages — not raw Python tracebacks.

### Decision
Define a typed exception hierarchy rooted at `PdfToolError`. The CLI layer catches all `PdfToolError` subclasses and renders them as Rich panels with a suggested fix.

### Reasons
- Enables precise error handling at each layer without leaking internal details.
- Makes the CLI professional-grade: users see "Missing dependency: libreoffice. Install with: `brew install libreoffice`" — not a `FileNotFoundError` traceback.
- Simplifies testing: tests can assert on specific exception types.

---

## ADR-010: Docker as a First-Class Distribution Target

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
The biggest pain point for users is installing system binaries (LibreOffice, Tesseract, Ghostscript). This is especially true in CI/CD environments.

### Decision
Maintain an official multi-architecture Docker image (`linux/amd64`, `linux/arm64`) published to GHCR with all system dependencies pre-installed.

### Reasons
- Zero-setup experience for Docker users and CI pipelines.
- Removes the friction of the `pdf-tool doctor` loop for automated environments.
- The Docker image becomes the canonical reference environment for testing.
- Multi-arch support covers both x86 servers and Apple Silicon (M-series) Macs.

---

## ADR-011: Short Tool Name `pdf` and Direct Conversion UX

- **Date:** 2026-10-27
- **Status:** ✅ Accepted

### Context
Typing `uv run pdf-tool convert input.png -o output.pdf` is unnecessarily verbose for high-frequency daily tasks. Users want the fastest possible workflow with minimal keystrokes.

### Decision
1. Register `pdf` as the primary executable entrypoint in `pyproject.toml` and symlink to `~/.local/bin/pdf`.
2. Implement `DefaultGroup` in Typer: any direct file argument passed to `pdf` without a subcommand automatically routes to `convert`.
3. Support positional input/output syntax (`pdf input.png output.pdf`).
4. Provide 1-letter command aliases (`m` for merge, `s` for split, `z` for compress, `doc` for doctor).

### Reasons
- Reduces typing by >70% for common tasks: `pdf photo.jpg` instantly produces `photo.pdf`.
- Retains full backwards compatibility with explicit subcommands (`pdf convert ...`).
- Matches modern ergonomic CLI tools like `git` and `docker`.

---

## ADR-012: Centralized User Configuration with Dot-Notation TOML

- **Date:** 2026-10-28
- **Status:** ✅ Accepted

### Context
Users require persistent configuration defaults across conversion sessions (e.g., preferred DPI for rasterization, default compression level, preferred OCR languages, and default output directories) without having to specify verbose CLI flags each run.

### Decision
Implement a persistent `ConfigManager` reading from and writing to `~/.pdf-tool/config.toml` using `tomllib` (Python standard library) and `tomli-w`. Expose a dedicated `pdf config` command suite (`show`, `get`, `set`, `reset`, `path`) and hierarchical dot-notation key addressing (`defaults.image_dpi`).

### Reasons
- TOML is human-readable, format-preserving, and the standard configuration format in the modern Python ecosystem.
- Dot-notation simplifies CLI interaction (`pdf config set defaults.image_dpi 200`).
- Strict type coercion maps string CLI inputs into appropriate primitive types (integers, booleans, floats).
- Non-destructive deep-merging ensures user overrides never erase newly introduced library defaults.

---

## ADR-013: Batch Processing Engine and Concurrency Model

- **Date:** 2026-10-28
- **Status:** ✅ Accepted

### Context
Users frequently convert batches of documents matching glob patterns (e.g. `*.docx` or `docs/*.md`). Executing conversions one-by-one sequentially is slow when operating on large document sets, and failures on single files should not abort the entire batch.

### Decision
1. Implement glob wildcard pattern expansion (`glob.glob`) in the `convert` CLI command.
2. Introduce a concurrency engine using `concurrent.futures.ThreadPoolExecutor` activated via `--parallel` (`-j`) with configurable `--workers`.
3. Isolate each batch conversion item in its own try/except boundary, recording execution duration, output size, status, and error descriptions.
4. Render progress using a live multi-column Rich `Progress` bar and display a comprehensive tabular batch summary report at completion.

### Reasons
- Python's `ThreadPoolExecutor` works seamlessly across all operating systems without process-spawning overhead or pickling limitations on complex adapters.
- Subprocess operations (LibreOffice, Ghostscript, Tesseract) and file I/O release the GIL, yielding near-linear multi-core speedups.
- Failure resilience guarantees that partial batches complete successfully, while returning exit code 1 to indicate any failed conversions to CI/CD pipelines.

---

## ADR-014: Multi-Stage Containerization with Headless Engines

- **Date:** 2026-10-28
- **Status:** ✅ Accepted

### Context
Several advanced conversion paths require external system binaries (`soffice`, `tesseract`, `gs`). Setting these up across disparate developer machines or CI environments can be difficult.

### Decision
Provide an official multi-stage `Dockerfile` targeting Debian Bookworm slim:
- **Build Stage:** Builds wheel distributions using `astral-sh/uv`.
- **Runtime Stage:** Installs headless LibreOffice (`libreoffice-nogui`, `libreoffice-writer`, `libreoffice-calc`), `ghostscript`, `tesseract-ocr`, `poppler-utils`, and core font packs (`fonts-dejavu-core`, `fonts-liberation`), runs as an unprivileged user, and sets `ENTRYPOINT ["pdf"]`.

### Reasons
- Minimizes final container footprint while including all runtime conversion capabilities.
- Prevents headless rendering font distortion or missing glyphs by pre-installing open-source document fonts.
- Multi-arch GHCR publishing supports deployment on both `linux/amd64` and `linux/arm64`.

---

*Last updated: 2026-10-28 | Add new ADRs at the bottom and update the Decision Index table.*
