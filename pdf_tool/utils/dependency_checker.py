"""System binary dependency checker."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from pdf_tool.exceptions import MissingDependencyError

# Install hints for known dependencies: {binary_name: {os: install_command}}
_INSTALL_HINTS: dict[str, dict[str, str]] = {
    "libreoffice": {
        "arch": "sudo pacman -S libreoffice-fresh",
        "ubuntu": "sudo apt install libreoffice",
        "macos": "brew install libreoffice",
        "windows": "choco install libreoffice",
    },
    "soffice": {
        "arch": "sudo pacman -S libreoffice-fresh",
        "ubuntu": "sudo apt install libreoffice",
        "macos": "brew install libreoffice",
        "windows": "choco install libreoffice",
    },
    "gs": {
        "arch": "sudo pacman -S ghostscript",
        "ubuntu": "sudo apt install ghostscript",
        "macos": "brew install ghostscript",
        "windows": "choco install ghostscript",
    },
    "ghostscript": {
        "arch": "sudo pacman -S ghostscript",
        "ubuntu": "sudo apt install ghostscript",
        "macos": "brew install ghostscript",
        "windows": "choco install ghostscript",
    },
    "tesseract": {
        "arch": "sudo pacman -S tesseract tesseract-data-eng",
        "ubuntu": "sudo apt install tesseract-ocr",
        "macos": "brew install tesseract",
        "windows": "choco install tesseract",
    },
    "mmdc": {
        "arch": "npm install -g @mermaid-js/mermaid-cli",
        "ubuntu": "npm install -g @mermaid-js/mermaid-cli",
        "macos": "brew install mermaid-cli",
        "windows": "npm install -g @mermaid-js/mermaid-cli",
    },
}


@dataclass
class DependencyStatus:
    """Status of a single system binary dependency.

    Attributes:
        name: Binary name (e.g. ``"gs"``).
        found: Whether the binary was found in PATH.
        path: Resolved absolute path, or ``None`` if not found.
    """

    name: str
    found: bool
    path: str | None


def check(binary_name: str) -> DependencyStatus:
    """Check whether *binary_name* is available in PATH.

    Args:
        binary_name: Name of the binary to look up (e.g. ``"gs"``).

    Returns:
        A :class:`DependencyStatus` describing the result.
    """
    resolved = shutil.which(binary_name)
    if not resolved and binary_name in ("soffice", "libreoffice"):
        alt = "libreoffice" if binary_name == "soffice" else "soffice"
        resolved = shutil.which(alt)
    elif not resolved and binary_name == "mmdc":
        nvm_dir = Path.home() / ".nvm" / "versions" / "node"
        if nvm_dir.exists():
            candidates = sorted(nvm_dir.glob("*/bin/mmdc"), reverse=True)
            if candidates:
                resolved = str(candidates[0])

    return DependencyStatus(name=binary_name, found=resolved is not None, path=resolved)


def verify(binary_names: list[str]) -> None:
    """Verify that every binary in *binary_names* is available.

    Raises:
        MissingDependencyError: For the first missing binary, with install hints.
    """
    for name in binary_names:
        status = check(name)
        if not status.found:
            hints = _INSTALL_HINTS.get(name, {})
            raise MissingDependencyError(dep_name=name, install_hints=hints)


def check_all(binary_names: list[str]) -> list[DependencyStatus]:
    """Return dependency status for all binaries without raising.

    Args:
        binary_names: List of binary names to check.

    Returns:
        List of :class:`DependencyStatus` objects (one per binary).
    """
    return [check(name) for name in binary_names]
