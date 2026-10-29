"""Abstract base adapter and ConversionResult dataclass."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConversionResult:
    """Metadata about a completed conversion operation.

    Attributes:
        input_path: Source file path.
        output_path: Destination file path.
        input_size_bytes: Size of the input file in bytes.
        output_size_bytes: Size of the output file in bytes.
        duration_seconds: Elapsed time for the conversion.
        engine: Name of the engine/library used.
    """

    input_path: Path
    output_path: Path
    input_size_bytes: int
    output_size_bytes: int
    duration_seconds: float
    engine: str


class BaseAdapter(ABC):
    """Abstract base class that every conversion adapter must implement."""

    @property
    @abstractmethod
    def required_system_deps(self) -> list[str]:
        """Return a list of system binary names required by this adapter."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Return a human-readable name for the underlying engine."""

    @abstractmethod
    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Execute the conversion.

        Args:
            input_path: Source file path.
            output_path: Destination file path.
            **options: Adapter-specific keyword options.

        Returns:
            A :class:`ConversionResult` with metadata about the operation.
        """

    def _make_result(
        self,
        input_path: Path,
        output_path: Path,
        start_time: float,
    ) -> ConversionResult:
        """Build a :class:`ConversionResult` from standard fields.

        Args:
            input_path: Source file path.
            output_path: Destination file path.
            start_time: :func:`time.monotonic` timestamp before conversion started.

        Returns:
            A populated :class:`ConversionResult`.
        """
        return ConversionResult(
            input_path=input_path,
            output_path=output_path,
            input_size_bytes=input_path.stat().st_size if input_path.exists() else 0,
            output_size_bytes=output_path.stat().st_size if output_path.exists() else 0,
            duration_seconds=time.monotonic() - start_time,
            engine=self.engine_name,
        )
