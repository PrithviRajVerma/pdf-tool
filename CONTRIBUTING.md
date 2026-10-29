# Contributing to pdf-tool

Thank you for your interest in contributing to `pdf-tool`! This guide explains how to set up your local development environment, run checks and tests, and add a new conversion adapter.

---

## 🛠️ Development Setup

We use [`uv`](https://github.com/astral-sh/uv) for fast and reproducible environment management.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/example/pdf-tool.git
   cd pdf-tool
   ```

2. **Install dependencies and create virtual environment:**
   ```bash
   uv sync --all-extras --dev
   ```

3. **Verify tests pass:**
   ```bash
   uv run pytest
   ```

---

## 🧪 Testing and Code Quality

We enforce strict formatting and linting via Ruff, and aim for ≥ 80% test coverage.

- **Lint code:**
  ```bash
  uv run ruff check .
  ```
- **Format code:**
  ```bash
  uv run ruff format .
  ```
- **Run tests with coverage:**
  ```bash
  uv run pytest --cov=pdf_tool --cov-report=term-missing
  ```

---

## 🧩 Adding a New Conversion Adapter

`pdf-tool` uses an extensible **Adapter pattern** registered in a central registry. To add support for a new conversion format (e.g. `epub → pdf`):

### Step 1: Create the Adapter Class

Create a new file under `pdf_tool/adapters/`, e.g. `pdf_tool/adapters/epub_to_pdf.py`:

```python
from pathlib import Path
from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.router.registry import registry
from pdf_tool.exceptions import ConversionFailedError


@registry.register(input_fmts=["epub"], output_fmt="pdf")
class EpubToPdfAdapter(BaseAdapter):
    @property
    def required_system_deps(self) -> list[str]:
        # Return any required CLI binary names (e.g., ["ebook-convert"]), or []
        return []

    @property
    def engine_name(self) -> str:
        return "EpubConverter"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        # Implement conversion logic here
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ...
        return ConversionResult(
            input_path=input_path,
            output_path=output_path,
            engine=self.engine_name,
            input_size_bytes=input_path.stat().st_size,
            output_size_bytes=output_path.stat().st_size,
            duration_seconds=elapsed,
        )
```

### Step 2: Export the Adapter

In `pdf_tool/adapters/__init__.py`, import your adapter so the `@registry.register` decorator executes on module import:

```python
import pdf_tool.adapters.epub_to_pdf  # noqa: F401
```

### Step 3: Register File Formats if Needed

If the input format is a document or image format that isn't standard, ensure `FileInspector` in `pdf_tool/router/file_inspector.py` recognizes the extension and MIME type.

### Step 4: Add Tests

Add integration and unit tests in `tests/integration/` or `tests/unit/`:
- Verify successful conversion.
- Test missing input handling and error cases.
- Test CLI interaction via `typer.testing.CliRunner`.

---

## 📦 Pull Request Process

1. Create a feature branch: `git checkout -b feat/my-new-adapter`.
2. Commit your changes with descriptive commit messages.
3. Verify that `uv run ruff check .` and `uv run pytest` pass cleanly.
4. Submit a Pull Request targeting the `master` / `main` branch.
