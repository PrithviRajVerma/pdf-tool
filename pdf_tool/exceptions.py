"""Typed exception hierarchy for pdf-tool."""

from __future__ import annotations


class PdfToolError(Exception):
    """Base exception for all pdf-tool errors."""


class MissingDependencyError(PdfToolError):
    """Raised when a required system binary is not found in PATH.

    Attributes:
        dep_name: Name of the missing dependency binary.
        install_hints: Dict mapping OS name to install command string.
    """

    def __init__(
        self,
        dep_name: str,
        install_hints: dict[str, str] | None = None,
        message: str | None = None,
    ) -> None:
        self.dep_name = dep_name
        self.install_hints: dict[str, str] = install_hints or {}
        msg = message or f"Required dependency '{dep_name}' not found in PATH."
        super().__init__(msg)


class UnsupportedConversionError(PdfToolError):
    """Raised when no adapter exists for the requested (input, output) format pair."""

    def __init__(self, input_fmt: str, output_fmt: str) -> None:
        self.input_fmt = input_fmt
        self.output_fmt = output_fmt
        super().__init__(f"No adapter registered for conversion: {input_fmt!r} → {output_fmt!r}")


class ConversionFailedError(PdfToolError):
    """Raised when the conversion engine returns a non-zero exit code or crashes."""


class InvalidInputError(PdfToolError):
    """Raised when the input file is corrupt, empty, or wrong format."""


class OutputValidationError(PdfToolError):
    """Raised when the output file fails post-conversion validation."""
