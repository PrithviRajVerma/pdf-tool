"""Markdown preprocessor for advanced formatting, table identification, and styling."""

from __future__ import annotations

import re


def protect_code_blocks(text: str) -> tuple[str, dict[str, str]]:
    """Extract fenced code blocks and replace them with unique placeholders.

    This ensures tables, metadata, or callouts inside code snippets are preserved untouched.
    """
    placeholders: dict[str, str] = {}

    def _replace(match: re.Match) -> str:
        key = f"<!--PDF_TOOL_CODE_BLOCK_{len(placeholders)}-->"
        placeholders[key] = match.group(0)
        return key

    pattern = re.compile(r"(```[\s\S]*?```|~~~[\s\S]*?~~~)")
    protected = pattern.sub(_replace, text)
    return protected, placeholders


def restore_code_blocks(text: str, placeholders: dict[str, str]) -> str:
    """Restore previously protected code blocks."""
    for key, val in placeholders.items():
        text = text.replace(key, val)
    return text


def convert_pandoc_multiline_tables(text: str) -> str:
    """Detect and convert Pandoc multiline and simple tables into standard GFM pipe tables.

    Recognizes:
    - Multiline tables with column boundary separators (e.g. `------ ------ ------`).
    - Optional top border (e.g. `-----------------------------------------`).
    - Multi-line cell continuations.
    - Blank line row separators.
    - Optional bottom border.
    """
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        header_idx = -1
        sep_idx = -1

        # Check for top border followed by header then col separators
        if re.match(r"^\s*[-]{3,}(\s+[-]{3,})*\s*$", line) and i + 2 < n:
            if re.match(r"^\s*[-]{3,}(\s+[-]{3,})+\s*$", lines[i + 2]):
                header_idx = i + 1
                sep_idx = i + 2
        # Check for header followed directly by col separators
        elif i + 1 < n and re.match(r"^\s*[-]{3,}(\s+[-]{3,})+\s*$", lines[i + 1]):
            header_cand = lines[i].strip()
            if header_cand and not header_cand.startswith(("#", "-", "*", ">")):
                header_idx = i
                sep_idx = i + 1

        if sep_idx == -1:
            result.append(line)
            i += 1
            continue

        sep_line = lines[sep_idx]
        col_matches = list(re.finditer(r"[-]{3,}", sep_line))
        if len(col_matches) < 2:
            result.append(line)
            i += 1
            continue

        # Determine column spans: (start, end)
        col_bounds: list[tuple[int, int | None]] = []
        for c_idx in range(len(col_matches)):
            start = col_matches[c_idx].start()
            if c_idx + 1 < len(col_matches):
                end = col_matches[c_idx + 1].start()
            else:
                end = None
            col_bounds.append((start, end))

        def _get_col_chunk(row_line: str, start: int, end: int | None) -> str:
            if start >= len(row_line):
                return ""
            if end is None:
                return row_line[start:].rstrip()
            return row_line[start:end].rstrip()

        headers = [_get_col_chunk(lines[header_idx], s, e).strip() for s, e in col_bounds]

        # Scan rows
        rows: list[list[str]] = []
        cur_row: list[str] = ["" for _ in col_bounds]
        row_line_idx = sep_idx + 1

        while row_line_idx < n:
            r_line = lines[row_line_idx]

            # Bottom boundary
            if re.match(r"^\s*[-]{3,}(\s+[-]{3,})*\s*$", r_line):
                if any(c.strip() for c in cur_row):
                    rows.append(cur_row)
                    cur_row = []
                row_line_idx += 1
                break

            # Heading terminates table
            if r_line.strip().startswith("#"):
                if any(c.strip() for c in cur_row):
                    rows.append(cur_row)
                    cur_row = []
                break

            # Blank line separates rows in multiline table
            if not r_line.strip():
                if any(c.strip() for c in cur_row):
                    rows.append(cur_row)
                    cur_row = ["" for _ in col_bounds]
                row_line_idx += 1
                continue

            # Check if this line starts a new row in a simple table (no blank lines)
            line_cols = [_get_col_chunk(r_line, s, e).strip() for s, e in col_bounds]
            if not any(c for c in cur_row):
                cur_row = line_cols
            else:
                # Continuation of current cell
                for c_i, val in enumerate(line_cols):
                    if val:
                        cur_row[c_i] = (cur_row[c_i] + " " + val).strip() if cur_row[c_i] else val
            row_line_idx += 1

        if any(c.strip() for c in cur_row):
            rows.append(cur_row)

        def _clean_cell(cell: str) -> str:
            # Escape pipes inside cells
            escaped = cell.replace("|", r"\|")
            # Replace multiple consecutive spaces with a single space
            return re.sub(r"\s+", " ", escaped).strip()

        # Build GFM pipe table
        header_str = "| " + " | ".join(_clean_cell(h) for h in headers) + " |"
        sep_str = "| " + " | ".join(":---" for _ in headers) + " |"
        table_lines = ["", header_str, sep_str]
        for row in rows:
            table_lines.append("| " + " | ".join(_clean_cell(c) for c in row) + " |")
        table_lines.append("")

        result.extend(table_lines)
        i = row_line_idx

    return "\n".join(result)


def convert_grid_tables(text: str) -> str:
    """Detect and convert Pandoc grid tables into GFM pipe tables."""
    lines = text.splitlines()
    result: list[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].rstrip()
        trimmed = line.strip()

        # Check if line looks like top of grid table
        if re.match(r"^\+[-+=]+\+$", trimmed):
            plus_indices = [idx for idx, ch in enumerate(trimmed) if ch == "+"]
            if len(plus_indices) >= 3 and i + 2 < n:
                col_bounds = [
                    (plus_indices[k], plus_indices[k + 1]) for k in range(len(plus_indices) - 1)
                ]
                headers: list[str] = []
                rows: list[list[str]] = []
                cur_row = ["" for _ in col_bounds]
                is_header = True
                row_idx = i + 1

                valid_grid = False
                while row_idx < n:
                    r_line = lines[row_idx].rstrip()
                    r_trimmed = r_line.strip()

                    if re.match(r"^\+[=+]+\+$", r_trimmed):
                        # Header separator
                        headers = [c.strip() for c in cur_row]
                        cur_row = ["" for _ in col_bounds]
                        is_header = False
                        row_idx += 1
                        continue
                    elif re.match(r"^\+[-+]+\+$", r_trimmed):
                        # Row separator or table end
                        if not is_header and any(c.strip() for c in cur_row):
                            rows.append([c.strip() for c in cur_row])
                            cur_row = ["" for _ in col_bounds]
                        row_idx += 1
                        if row_idx >= n or not lines[row_idx].strip().startswith(("+", "|")):
                            valid_grid = True
                            break
                        continue
                    elif r_trimmed.startswith("|") and r_trimmed.endswith("|"):
                        for c_i, (s, e) in enumerate(col_bounds):
                            chunk = r_line[s + 1 : e].strip() if s < len(r_line) else ""
                            cur_row[c_i] = (
                                (cur_row[c_i] + " " + chunk).strip() if cur_row[c_i] else chunk
                            )
                        row_idx += 1
                    else:
                        break

                if valid_grid and headers and rows:

                    def _clean(c: str) -> str:
                        return c.replace("|", r"\|").strip()

                    result.append("")
                    result.append("| " + " | ".join(_clean(h) for h in headers) + " |")
                    result.append("| " + " | ".join(":---" for _ in headers) + " |")
                    for r in rows:
                        result.append("| " + " | ".join(_clean(c) for c in r) + " |")
                    result.append("")
                    i = row_idx
                    continue

        result.append(line)
        i += 1

    return "\n".join(result)


def convert_metadata_cards(text: str) -> str:
    """Detect leading document metadata (e.g. **Key:** Value) under the main title.

    Wraps it in a semantic <div class="document-metadata-card"> for sleek executive presentation.
    """
    pattern = re.compile(
        r"(#\s+[^\n]+\n+)(\*\*([A-Za-z0-9 _-]+):\*\*[^\n]+(?:\n(?!\n|#)[^\n]+)*)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return text

    h1_part = match.group(1)
    meta_part = match.group(2)

    raw_entries = re.findall(
        r"\*\*([A-Za-z0-9 _-]+):\*\*\s*([^\*]+?)(?=\*\*|\Z)", meta_part, re.DOTALL
    )
    if len(raw_entries) < 2:
        return text

    dl_items: list[str] = []
    for k, v in raw_entries:
        cleaned_val = " ".join(v.replace("\\", " ").split())
        dl_items.append(f"<dt>{k.strip()}</dt><dd>{cleaned_val.strip()}</dd>")

    card_html = (
        '<div class="document-metadata-card"><dl>\n' + "\n".join(dl_items) + "\n</dl></div>\n"
    )

    return text[: match.start()] + h1_part + "\n" + card_html + "\n" + text[match.end() :]


def convert_callouts(text: str) -> str:
    """Convert GitHub-style blockquote callouts (> [!NOTE], > [!WARNING], etc.) to styled cards."""
    pattern = re.compile(
        r"^(?:>[ \t]*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\][ \t]*\n)((?:>[ \t]*[^\n]*\n?)+)",
        re.MULTILINE | re.IGNORECASE,
    )

    def _replace(match: re.Match) -> str:
        callout_type = match.group(1).lower()
        title = match.group(1).upper()
        raw_lines = match.group(2).splitlines()
        content_lines = []
        for raw_line in raw_lines:
            stripped = raw_line.lstrip()
            if stripped.startswith(">"):
                stripped = stripped[1:].lstrip()
            content_lines.append(stripped)

        content = " ".join(content_lines).strip()
        return (
            f'<div class="callout callout-{callout_type}">'
            f'<div class="callout-title">{title}</div>'
            f"<p>{content}</p>"
            f"</div>\n\n"
        )

    return pattern.sub(_replace, text)


def scope_svg_ids(svg: str, prefix: str) -> str:
    """Namespace element IDs and intra-SVG URL/href references.

    Eliminates WeasyPrint duplicate anchor warnings and cross-diagram collisions
    without modifying the diagram's root SVG ID or breaking its CSS style selectors.
    """
    if not svg or not prefix:
        return svg

    # Find all id="..." attributes
    ids = set(re.findall(r"""\bid=["']([^"']+)["']""", svg))
    for el_id in sorted(ids, key=len, reverse=True):
        if el_id == prefix or el_id.startswith(f"{prefix}_") or el_id.startswith(f"{prefix}-"):
            continue
        new_id = f"{prefix}_{el_id}"
        # Replace id="el_id"
        svg = re.sub(rf"""\bid=(["']){re.escape(el_id)}\1""", f"""id=\\1{new_id}\\1""", svg)
        # Replace href="#el_id", url(#el_id), url("#el_id")
        svg = re.sub(rf"""(#){re.escape(el_id)}(["'\)])""", f"""\\1{new_id}\\2""", svg)

    # Deduplicate any identical IDs that occur multiple times within this single SVG
    seen_ids: set[str] = set()

    def _dedup_id(match: re.Match) -> str:
        quote = match.group(1)
        raw_id = match.group(2)
        if raw_id == prefix:
            return match.group(0)
        if raw_id in seen_ids:
            count = 1
            while f"{raw_id}_{count}" in seen_ids:
                count += 1
            unique_id = f"{raw_id}_{count}"
            seen_ids.add(unique_id)
            return f"id={quote}{unique_id}{quote}"
        seen_ids.add(raw_id)
        return match.group(0)

    svg = re.sub(r"""\bid=(["'])([^"']+)\1""", _dedup_id, svg)

    return svg


def preprocess_markdown(text: str) -> str:
    """Run the complete preprocessing pipeline on Markdown content."""
    protected, placeholders = protect_code_blocks(text)
    processed = convert_metadata_cards(protected)
    processed = convert_pandoc_multiline_tables(processed)
    processed = convert_grid_tables(processed)
    processed = convert_callouts(processed)
    restored = restore_code_blocks(processed, placeholders)
    return restored
