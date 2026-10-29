"""Markdown to PDF adapter using markdown-it-py and WeasyPrint."""

from __future__ import annotations

import concurrent.futures
import shutil
import subprocess
import time
from pathlib import Path

import pygments
import pygments.formatters
import pygments.lexers
import weasyprint
from markdown_it import MarkdownIt

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry

_DEFAULT_CSS = """
@page {
    size: A4;
    margin: 20mm;
    @bottom-right {
        content: counter(page);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 8pt;
        color: #718096;
    }
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.6;
    color: #2d3748;
    margin: 0;
    padding: 0;
}

h1, h2, h3, h4, h5, h6 {
    color: #1a202c;
    font-weight: 600;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

h1 { font-size: 20pt; border-bottom: 1.5px solid #e2e8f0; padding-bottom: 0.3em; margin-top: 0; }
h2 { font-size: 15pt; border-bottom: 1px solid #edf2f7; padding-bottom: 0.2em; }
h3 { font-size: 13pt; }
h4 { font-size: 11pt; }

p, ul, ol, dl, table, pre, blockquote {
    margin-top: 0;
    margin-bottom: 1em;
}

code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 85%;
    padding: 0.2em 0.4em;
    margin: 0;
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    color: #c53030;
}

pre {
    background-color: #f7fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 12px 16px;
    page-break-inside: avoid;
}

pre code {
    background-color: transparent;
    border: 0;
    padding: 0;
    color: inherit;
    font-size: 9pt;
}

blockquote {
    border-left: 4px solid #4299e1;
    padding-left: 14px;
    color: #4a5568;
    margin-left: 0;
    font-style: italic;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin-bottom: 1.5em;
    page-break-inside: avoid;
}

table, th, td {
    border: 1px solid #e2e8f0;
}

th, td {
    padding: 8px 12px;
    text-align: left;
    font-size: 9.5pt;
}

th {
    background-color: #edf2f7;
    font-weight: 600;
    color: #2d3748;
}

tr:nth-child(even) {
    background-color: #f7fafc;
}

img {
    max-width: 100%;
    height: auto;
    page-break-inside: avoid;
}

hr {
    border: 0;
    height: 1px;
    background: #e2e8f0;
    margin: 2em 0;
}

.mermaid-diagram {
    text-align: center;
    margin: 1.5em 0;
    page-break-inside: avoid;
}

.mermaid-diagram svg {
    max-width: 100%;
    max-height: 240mm;
    height: auto;
    display: inline-block;
    margin: 0 auto;
}
"""


def find_mmdc_binary() -> str | None:
    """Find the mermaid-cli (mmdc) executable path."""
    found = shutil.which("mmdc")
    if found:
        return found
    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        candidates = sorted(nvm_dir.glob("*/bin/mmdc"), reverse=True)
        if candidates:
            return str(candidates[0])
    return None


def render_mermaid_to_svg(code: str, timeout: float = 15.0) -> str | None:
    """Render Mermaid diagram code to SVG string using mmdc."""
    mmdc_path = find_mmdc_binary()
    if not mmdc_path:
        return None

    try:
        proc = subprocess.run(
            [
                mmdc_path,
                "-i",
                "-",
                "-o",
                "-",
                "-e",
                "svg",
                "-b",
                "transparent",
                "--no-font-embed",
                "-q",
            ],
            input=code,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip().startswith("<svg"):
            return proc.stdout.strip()
    except Exception:
        return None
    return None


def _highlight_code(code: str, lang: str, _attrs: str) -> str:
    """Highlight code syntax using Pygments for MarkdownIt fenced blocks."""
    if lang:
        try:
            lexer = pygments.lexers.get_lexer_by_name(lang)
            formatter = pygments.formatters.HtmlFormatter(nowrap=True)
            return pygments.highlight(code, lexer, formatter)
        except Exception:
            pass
    return ""


@registry.register(input_fmts=["md", "markdown"], output_fmt="pdf")
class MarkdownToPdfAdapter(BaseAdapter):
    """Converts Markdown documents to clean, professionally-styled PDF documents."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "WeasyPrint"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert a Markdown file to PDF.

        Args:
            input_path: Path to the .md file.
            output_path: Path to the target .pdf file.
            **options:
                css (str | None): Optional custom CSS stylesheet string or path.

        Returns:
            ConversionResult with timing and file size metadata.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"Markdown file not found: '{input_path}'")

        try:
            content = input_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise InvalidInputError(f"Failed to read Markdown file '{input_path}': {exc}") from exc

        # Setup Markdown parser with extensions
        md = MarkdownIt(
            "commonmark",
            {"highlight": _highlight_code, "typographer": True},
        ).enable(["table", "strikethrough"])

        tokens = md.parse(content)

        # Pre-render all unique Mermaid blocks in parallel for high performance
        mermaid_blocks: list[str] = []
        for token in tokens:
            if token.type == "fence":
                info = token.info.strip().lower()
                lang = info.split()[0] if info else ""
                if lang == "mermaid" and token.content:
                    mermaid_blocks.append(token.content)

        diagram_cache: dict[str, str | None] = {}
        if mermaid_blocks:
            unique_blocks = list(dict.fromkeys(mermaid_blocks))
            max_workers = min(8, len(unique_blocks))
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                rendered_svgs = list(executor.map(render_mermaid_to_svg, unique_blocks))
                for block, svg in zip(unique_blocks, rendered_svgs):
                    diagram_cache[block] = svg

        default_fence = md.renderer.rules.get("fence")

        def custom_fence(tokens, idx, opts, env):
            token = tokens[idx]
            info = token.info.strip().lower()
            lang = info.split()[0] if info else ""
            if lang == "mermaid":
                svg = diagram_cache.get(token.content)
                if svg:
                    return f'<div class="mermaid-diagram">{svg}</div>\n'
            if default_fence:
                return default_fence(tokens, idx, opts, env)
            return f"<pre><code>{token.content}</code></pre>"

        md.renderer.rules["fence"] = custom_fence

        rendered_html = md.renderer.render(tokens, md.options, {})
        pygments_css = pygments.formatters.HtmlFormatter().get_style_defs(".highlight")
        custom_css = options.get("css", "")

        full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        {_DEFAULT_CSS}
        {pygments_css}
        {custom_css}
    </style>
</head>
<body>
    {rendered_html}
</body>
</html>
"""

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            doc = weasyprint.HTML(string=full_html, base_url=str(input_path.parent))
            doc.write_pdf(target=str(output_path))
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to render PDF from Markdown '{input_path.name}': {exc}"
            ) from exc

        return self._make_result(input_path, output_path, start)
