"""Markdown to PDF adapter using markdown-it-py and WeasyPrint."""

from __future__ import annotations

import concurrent.futures
import re
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
from pdf_tool.adapters.markdown_preprocessor import preprocess_markdown, scope_svg_ids
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry

_DEFAULT_CSS = """
@page {
    size: A4;
    margin: 22mm 18mm 20mm 18mm;
    @top-left {
        content: string(doctitle);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 7.5pt;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 0.5pt solid #e2e8f0;
        padding-bottom: 3mm;
    }
    @top-right {
        content: string(sectiontitle);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 7.5pt;
        color: #94a3b8;
        border-bottom: 0.5pt solid #e2e8f0;
        padding-bottom: 3mm;
    }
    @bottom-left {
        content: "CONFIDENTIAL & PROPRIETARY";
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 7pt;
        font-weight: 500;
        color: #94a3b8;
        letter-spacing: 0.05em;
        border-top: 0.5pt solid #e2e8f0;
        padding-top: 3mm;
    }
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 7.5pt;
        font-weight: 500;
        color: #64748b;
        border-top: 0.5pt solid #e2e8f0;
        padding-top: 3mm;
    }
}

@page:first {
    margin-top: 18mm;
    @top-left { content: none; border-bottom: none; }
    @top-right { content: none; border-bottom: none; }
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.55;
    color: #334155;
    margin: 0;
    padding: 0;
    orphans: 3;
    widows: 3;
}

h1, h2, h3, h4, h5, h6 {
    color: #0f172a;
    font-weight: 600;
    margin-top: 1.5em;
    margin-bottom: 0.4em;
    page-break-after: avoid;
    break-after: avoid;
}

h1 + p, h2 + p, h3 + p, h4 + p {
    page-break-after: avoid;
    break-after: avoid;
}

h1 {
    string-set: doctitle content();
    font-size: 21pt;
    font-weight: 700;
    letter-spacing: -0.025em;
    line-height: 1.25;
    border-bottom: 2.5px solid #2563eb;
    padding-bottom: 0.35em;
    margin-top: 0;
    margin-bottom: 0.6em;
}

h2 {
    string-set: sectiontitle content();
    font-size: 13.5pt;
    color: #1e293b;
    letter-spacing: -0.015em;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 0.25em;
    margin-top: 1.8em;
    margin-bottom: 0.45em;
}

h3 {
    font-size: 11pt;
    color: #334155;
    margin-top: 1.3em;
    margin-bottom: 0.35em;
}

h4 {
    font-size: 9.5pt;
    color: #475569;
    margin-top: 1em;
    margin-bottom: 0.3em;
}

p, ul, ol, dl, table, pre, blockquote {
    margin-top: 0;
    margin-bottom: 0.9em;
}

ul, ol {
    padding-left: 20px;
}

li {
    margin-bottom: 0.25em;
}

li > p {
    margin-bottom: 0.25em;
}

code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 82%;
    padding: 0.15em 0.35em;
    margin: 0;
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 4px;
    color: #0284c7;
}

pre {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 10px 14px;
    margin: 1em 0;
    page-break-inside: avoid;
    break-inside: avoid;
    line-height: 1.45;
}

pre code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    background-color: transparent;
    border: 0;
    padding: 0;
    color: #1e293b;
    font-size: 8pt;
    tab-size: 2;
}

blockquote {
    border-left: 4px solid #3b82f6;
    padding: 8px 14px;
    background-color: #f8fafc;
    color: #475569;
    margin: 1em 0;
    font-style: italic;
    border-radius: 0 4px 4px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin-top: 0.8em;
    margin-bottom: 1.5em;
    font-size: 8.5pt;
    line-height: 1.45;
    page-break-inside: auto;
}

thead {
    display: table-header-group;
}

tr {
    page-break-inside: avoid;
    page-break-after: auto;
}

th {
    background-color: #f8fafc;
    color: #0f172a;
    font-weight: 600;
    font-size: 8.5pt;
    padding: 8px 10px;
    border-top: 1.5px solid #cbd5e1;
    border-bottom: 2px solid #64748b;
    border-left: none;
    border-right: none;
    text-align: left;
    vertical-align: bottom;
}

td {
    padding: 7px 10px;
    border-top: 1px solid #f1f5f9;
    border-bottom: 1px solid #e2e8f0;
    border-left: none;
    border-right: none;
    vertical-align: top;
    color: #334155;
}

tr:nth-child(even) td {
    background-color: #f8fafc;
}

td code {
    font-size: 7.5pt;
    padding: 1px 4px;
    white-space: normal;
    overflow-wrap: break-word;
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #0284c7;
    border-radius: 3px;
}

.document-metadata-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #2563eb;
    border-radius: 6px;
    padding: 10px 16px;
    margin: 0.8em 0 1.6em 0;
    page-break-inside: avoid;
}

.document-metadata-card dl {
    display: grid;
    grid-template-columns: 140px 1fr;
    row-gap: 5px;
    column-gap: 12px;
    margin: 0;
    padding: 0;
    font-size: 8.5pt;
    line-height: 1.4;
}

.document-metadata-card dt {
    font-weight: 600;
    color: #475569;
    margin: 0;
}

.document-metadata-card dd {
    margin: 0;
    color: #0f172a;
}

.callout {
    margin: 1.2em 0;
    padding: 10px 14px;
    border-radius: 6px;
    border-left: 4px solid #3b82f6;
    background: #eff6ff;
    page-break-inside: avoid;
    font-size: 9pt;
}

.callout-title {
    font-weight: 700;
    margin-bottom: 4px;
    color: #1e40af;
    text-transform: uppercase;
    font-size: 7.5pt;
    letter-spacing: 0.05em;
}

.callout p {
    margin: 0;
    color: #1e3a8a;
}

.callout.callout-tip { border-left-color: #10b981; background: #ecfdf5; }
.callout.callout-tip .callout-title { color: #065f46; }
.callout.callout-tip p { color: #064e3b; }
.callout.callout-warning { border-left-color: #f59e0b; background: #fffbeb; }
.callout.callout-warning .callout-title { color: #92400e; }
.callout.callout-warning p { color: #78350f; }
.callout.callout-important { border-left-color: #8b5cf6; background: #f5f3ff; }
.callout.callout-important .callout-title { color: #5b21b6; }
.callout.callout-important p { color: #4c1d95; }
.callout.callout-caution { border-left-color: #ef4444; background: #fef2f2; }
.callout.callout-caution .callout-title { color: #991b1b; }
.callout.callout-caution p { color: #7f1d1d; }

img {
    max-width: 100%;
    height: auto;
    page-break-inside: avoid;
}

hr {
    border: 0;
    height: 1px;
    background: #e2e8f0;
    margin: 1.8em 0;
}

.mermaid-diagram {
    text-align: center;
    margin: 1.5em 0;
    page-break-inside: avoid;
    break-inside: avoid;
}

.mermaid-diagram svg {
    max-width: 100%;
    max-height: 215mm;
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


def _sanitize_mermaid(code: str) -> str:
    """Sanitize common Mermaid syntax quirks.

    - Unquoted edge labels containing parentheses.
    - Invalid sequence diagram bidirectional arrows (<->> instead of <<->>).
    - Unescaped semicolons inside sequence diagram message labels and notes.
    """

    def quote_edge_label(match: re.Match) -> str:
        inner = match.group(1).strip()
        if inner.startswith('"') and inner.endswith('"'):
            return f"|{inner}|"
        inner_cleaned = inner.replace('"', "'")
        return f'|"{inner_cleaned}"|'

    code = re.sub(r"\|([^|\r\n]*\([^|\r\n]*\)[^|\r\n]*)\|", quote_edge_label, code)
    code = re.sub(r"(\w+)\s*<->>\s*(\w+)", r"\1<<->>\2", code)

    lines = []
    is_sequence = "sequenceDiagram" in code
    for line in code.split("\n"):
        if is_sequence and ":" in line and not line.strip().startswith("%%"):
            parts = line.split(":", 1)
            left_lower = parts[0].lower()
            if any(k in left_lower for k in ["->", "--", "note", "activate", "deactivate"]):
                line = parts[0] + ":" + parts[1].replace(";", "#59;")
        lines.append(line)

    return "\n".join(lines)


def render_mermaid_to_svg(
    code: str, timeout: float = 15.0, svg_id: str | None = None
) -> str | None:
    """Render Mermaid diagram code to SVG string using mmdc."""
    mmdc_path = find_mmdc_binary()
    if not mmdc_path:
        return None

    cmd = [
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
    ]

    config_path = Path(__file__).parent / "mermaid_config.json"
    if not config_path.exists():
        try:
            config_path.write_text(
                '{\n  "flowchart": {\n    "htmlLabels": false\n  },\n  "htmlLabels": false\n}\n',
                encoding="utf-8",
            )
        except Exception:
            temp_config = Path("/tmp/pdf_tool_mermaid_config.json")
            if not temp_config.exists():
                try:
                    temp_config.write_text(
                        '{"flowchart": {"htmlLabels": false}, "htmlLabels": false}',
                        encoding="utf-8",
                    )
                except Exception:
                    pass
            config_path = temp_config

    if config_path.exists():
        cmd.extend(["-c", str(config_path)])

    if svg_id:
        cmd.extend(["-I", svg_id])

    try:
        proc = subprocess.run(
            cmd,
            input=code,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip().startswith("<svg"):
            return proc.stdout.strip()

        # Retry with sanitized syntax if first attempt failed
        sanitized = _sanitize_mermaid(code)
        if sanitized != code:
            proc_retry = subprocess.run(
                cmd,
                input=sanitized,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            if proc_retry.returncode == 0 and proc_retry.stdout.strip().startswith("<svg"):
                return proc_retry.stdout.strip()
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

        # Preprocess Markdown content for tables, metadata cards, and callouts
        content = preprocess_markdown(content)

        # Setup Markdown parser with extensions
        md = MarkdownIt(
            "commonmark",
            {"highlight": _highlight_code, "typographer": True},
        ).enable(["table", "strikethrough", "replacements", "smartquotes"])

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

            def _render_worker(item: tuple[int, str]) -> tuple[str, str | None]:
                idx, block = item
                svg_prefix = f"mermaid-diag-{idx}"
                svg = render_mermaid_to_svg(block, svg_id=svg_prefix)
                if svg:
                    svg = scope_svg_ids(svg, svg_prefix)
                return block, svg

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                for block, svg in executor.map(_render_worker, enumerate(unique_blocks)):
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
        formatter = pygments.formatters.HtmlFormatter()
        pygments_css = (
            formatter.get_style_defs("pre code") + "\n" + formatter.get_style_defs(".highlight")
        )
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
