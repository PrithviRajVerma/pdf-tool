"""Utility to parse human-readable file size strings (e.g. '2MB', '500KB')."""

from __future__ import annotations

import re

_SIZE_RE = re.compile(r"^([0-9.]+)\s*([KMG]?B?)$", re.IGNORECASE)
_MULTIPLIERS = {
    "": 1,
    "B": 1,
    "K": 1024,
    "KB": 1024,
    "M": 1024**2,
    "MB": 1024**2,
    "G": 1024**3,
    "GB": 1024**3,
}


def parse_size_bytes(size_str: str) -> int:
    """Parse a size string like '2MB', '500KB', '100B' into bytes.

    Args:
        size_str: Human-readable size string.

    Returns:
        Integer number of bytes.

    Raises:
        ValueError: If the format is invalid or cannot be parsed.
    """
    clean_str = size_str.strip()
    match = _SIZE_RE.match(clean_str)
    if not match:
        raise ValueError(
            f"Invalid size string '{size_str}'. Expected format like '500KB', '2MB', or '1GB'."
        )
    num_part, unit_part = match.groups()
    try:
        val = float(num_part)
    except ValueError as exc:
        raise ValueError(f"Invalid numeric value in size string '{size_str}'") from exc

    multiplier = _MULTIPLIERS.get(unit_part.upper(), 1)
    return int(val * multiplier)
