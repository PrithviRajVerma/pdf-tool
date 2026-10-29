"""Integration tests for Markdown to PDF conversion."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz
import pytest

from pdf_tool.adapters.markdown_to_pdf import MarkdownToPdfAdapter
from pdf_tool.exceptions import InvalidInputError
from pdf_tool.utils.output_validator import validate_pdf


def test_markdown_basic_to_pdf(tmp_path: Path) -> None:
    """Basic markdown document converts to a valid PDF."""
    md_file = tmp_path / "simple.md"
    md_file.write_text("# Title\n\nParagraph with **bold** text.", encoding="utf-8")
    out_pdf = tmp_path / "simple.pdf"

    adapter = MarkdownToPdfAdapter()
    result = adapter.convert(md_file, out_pdf)

    assert result.output_path.exists()
    validate_pdf(result.output_path)

    doc = fitz.open(str(result.output_path))
    assert doc.page_count >= 1
    text = doc[0].get_text()
    assert "Title" in text
    assert "Paragraph with" in text
    doc.close()


def test_markdown_with_code_and_tables(tmp_path: Path) -> None:
    """Markdown with tables and highlighted code blocks renders properly."""
    md_file = tmp_path / "rich.md"
    md_content = """# Developer Documentation

Here is a function:

```python
def calculate(a, b):
    return a + b
```

| Syntax | Description |
| ----------- | ----------- |
| Header | Title |
| Paragraph | Text |

> Important callout block.
"""
    md_file.write_text(md_content, encoding="utf-8")
    out_pdf = tmp_path / "rich.pdf"

    adapter = MarkdownToPdfAdapter()
    result = adapter.convert(md_file, out_pdf)

    assert result.output_path.exists()
    validate_pdf(result.output_path)

    doc = fitz.open(str(result.output_path))
    text = doc[0].get_text()
    assert "Developer Documentation" in text
    assert "calculate" in text
    assert "Syntax" in text
    doc.close()


def test_markdown_nonexistent_file(tmp_path: Path) -> None:
    """Converting nonexistent markdown file raises InvalidInputError."""
    missing_file = tmp_path / "nonexistent.md"
    out_pdf = tmp_path / "out.pdf"

    adapter = MarkdownToPdfAdapter()
    with pytest.raises(InvalidInputError):
        adapter.convert(missing_file, out_pdf)


def test_markdown_with_mermaid_diagram(tmp_path: Path) -> None:
    """Markdown with Mermaid flowchart diagram compiles and renders properly."""
    md_file = tmp_path / "diagram.md"
    md_content = """# Architecture Flow

```mermaid
flowchart TD
    A[Input Document] --> B[Parser]
    B --> C[PDF Output]
```

Regular text after diagram.
"""
    md_file.write_text(md_content, encoding="utf-8")
    out_pdf = tmp_path / "diagram.pdf"

    adapter = MarkdownToPdfAdapter()
    result = adapter.convert(md_file, out_pdf)

    assert result.output_path.exists()
    validate_pdf(result.output_path)

    doc = fitz.open(str(result.output_path))
    assert doc.page_count >= 1
    text = doc[0].get_text()
    assert "Architecture Flow" in text
    assert "Regular text after diagram" in text
    doc.close()


def test_markdown_with_invalid_mermaid_fallback(tmp_path: Path) -> None:
    """Markdown with syntax-broken Mermaid diagram falls back cleanly without failing."""
    md_file = tmp_path / "broken_diagram.md"
    md_content = """# Broken Diagram

```mermaid
flowchart TD === broken syntax here ===
```

End of document.
"""
    md_file.write_text(md_content, encoding="utf-8")
    out_pdf = tmp_path / "broken_diagram.pdf"

    adapter = MarkdownToPdfAdapter()
    result = adapter.convert(md_file, out_pdf)

    assert result.output_path.exists()
    validate_pdf(result.output_path)
