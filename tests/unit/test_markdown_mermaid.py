"""Unit tests for Mermaid diagram rendering and CLI detection."""

from __future__ import annotations

from unittest.mock import patch

from pdf_tool.adapters.markdown_to_pdf import (
    _sanitize_mermaid,
    find_mmdc_binary,
    render_mermaid_to_svg,
)


def test_find_mmdc_binary():
    # Should resolve binary path
    path = find_mmdc_binary()
    assert path is not None
    assert "mmdc" in path


def test_sanitize_mermaid():
    raw = "graph LR\n  A -->|Some (unquoted) label| B\n  C -.->|Already (quoted)| D\n  E ==>|\"Quoted (test)\"| F"
    sanitized = _sanitize_mermaid(raw)
    assert 'A -->|"Some (unquoted) label"| B' in sanitized
    assert 'C -.->|"Already (quoted)"| D' in sanitized
    assert 'E ==>|"Quoted (test)"| F' in sanitized


def test_render_mermaid_to_svg_success():
    code = "flowchart TD\n  NodeA --> NodeB\n"
    svg = render_mermaid_to_svg(code)
    assert svg is not None
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_render_mermaid_to_svg_with_parentheses_retry():
    # Unquoted parentheses in edge label would normally fail in mmdc without sanitization
    code = "graph TD\n  Redis -.->|Cache-Aside (Phase 5)| App\n"
    svg = render_mermaid_to_svg(code)
    assert svg is not None
    assert svg.startswith("<svg")
    assert "</svg>" in svg


def test_render_mermaid_to_svg_syntax_error():
    code = "flowchart TD === completely invalid ==="
    svg = render_mermaid_to_svg(code)
    assert svg is None


def test_render_mermaid_to_svg_missing_binary():
    with patch("pdf_tool.adapters.markdown_to_pdf.find_mmdc_binary", return_value=None):
        svg = render_mermaid_to_svg("flowchart TD\n A --> B")
        assert svg is None
