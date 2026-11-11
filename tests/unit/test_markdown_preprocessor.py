"""Unit tests for Markdown preprocessor (table detection, metadata, callouts, SVG scoping)."""

from __future__ import annotations

from pdf_tool.adapters.markdown_preprocessor import (
    convert_callouts,
    convert_grid_tables,
    convert_metadata_cards,
    convert_pandoc_multiline_tables,
    preprocess_markdown,
    scope_svg_ids,
)


def test_convert_pandoc_multiline_tables_basic():
    raw = """
  -----------------------------------------------------------------------
  Area                    Decision                Reason
  ----------------------- ----------------------- -----------------------
  Web client              Next.js, React,         Strong web application
                          TypeScript              foundation

  UI                      Tailwind CSS,           Accessible components
                          shadcn/ui, next-themes  and light/dark themes
  -----------------------------------------------------------------------
"""
    converted = convert_pandoc_multiline_tables(raw)
    assert "| Area | Decision | Reason |" in converted
    assert "| :--- | :--- | :--- |" in converted
    assert (
        "| Web client | Next.js, React, TypeScript | Strong web application foundation |"
        in converted
    )
    assert (
        "| UI | Tailwind CSS, shadcn/ui, next-themes | Accessible components and light/dark themes |"
        in converted
    )


def test_convert_grid_tables():
    raw = """
+-----------------+-----------------+
| Header 1        | Header 2        |
+=================+=================+
| Value 1         | Value 2         |
| continuation    | text            |
+-----------------+-----------------+
| Value 3         | Value 4         |
+-----------------+-----------------+
"""
    converted = convert_grid_tables(raw)
    assert "| Header 1 | Header 2 |" in converted
    assert "| :--- | :--- |" in converted
    assert "| Value 1 continuation | Value 2 text |" in converted
    assert "| Value 3 | Value 4 |" in converted


def test_convert_metadata_cards():
    raw = """# System Architecture

**Version:** 2.0\\
**Status:** Approved for production\\
**Author:** Engineering Team

## 1. Overview
"""
    converted = convert_metadata_cards(raw)
    assert '<div class="document-metadata-card">' in converted
    assert "<dt>Version</dt><dd>2.0</dd>" in converted
    assert "<dt>Status</dt><dd>Approved for production</dd>" in converted
    assert "<dt>Author</dt><dd>Engineering Team</dd>" in converted


def test_convert_callouts():
    raw = """> [!NOTE]
> This is a critical architectural decision.
> It spans multiple lines.
"""
    converted = convert_callouts(raw)
    assert '<div class="callout callout-note">' in converted
    assert '<div class="callout-title">NOTE</div>' in converted
    assert "This is a critical architectural decision. It spans multiple lines." in converted


def test_code_blocks_protected_from_table_conversion():
    raw = """Here is some code:

```text
------------------------------------------------
Not a table even with dashes
------------------------------------------------
```

Actual table:

  ----------------------- -----------------------
  ColA                    ColB
  ----------------------- -----------------------
  ValA                    ValB
  ----------------------- -----------------------
"""
    processed = preprocess_markdown(raw)
    assert (
        "```text\n------------------------------------------------\nNot a table even with dashes\n------------------------------------------------\n```"
        in processed
    )
    assert "| ColA | ColB |" in processed
    assert "| ValA | ValB |" in processed


def test_scope_svg_ids():
    raw_svg = '<svg id="root"><g id="actor0"><path href="#actor0"/><marker id="arrowhead"/></g><path marker-end="url(#arrowhead)"/></svg>'
    scoped = scope_svg_ids(raw_svg, "diag-1")
    assert 'id="diag-1_root"' in scoped
    assert 'id="diag-1_actor0"' in scoped
    assert 'href="#diag-1_actor0"' in scoped
    assert 'id="diag-1_arrowhead"' in scoped
    assert "url(#diag-1_arrowhead)" in scoped

    # When prefix matches root SVG id (as emitted by mmdc -I prefix), preserve root id for CSS selectors
    mermaid_svg = '<svg id="diag-1"><style>#diag-1 .node { fill: #fff; }</style><g id="actor0"><path id="stick"/><path id="stick"/></g></svg>'
    scoped_mermaid = scope_svg_ids(mermaid_svg, "diag-1")
    assert '<svg id="diag-1">' in scoped_mermaid
    assert "#diag-1 .node" in scoped_mermaid
    assert 'id="diag-1_actor0"' in scoped_mermaid
    assert 'id="diag-1_stick"' in scoped_mermaid
    assert 'id="diag-1_stick_1"' in scoped_mermaid
