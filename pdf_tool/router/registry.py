"""Adapter registry — maps (input_fmt, output_fmt) pairs to adapter classes."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

from pdf_tool.exceptions import UnsupportedConversionError

if TYPE_CHECKING:
    from pdf_tool.adapters.base import BaseAdapter

_AdapterT = TypeVar("_AdapterT", bound="type[BaseAdapter]")


class ConversionRegistry:
    """Singleton registry that maps format pairs to adapter classes.

    Adapters register themselves using the :meth:`register` decorator::

        @registry.register(input_fmts=["jpeg", "png"], output_fmt="pdf")
        class ImageToPdfAdapter(BaseAdapter):
            ...
    """

    _instance: ConversionRegistry | None = None

    def __new__(cls) -> ConversionRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry: dict[tuple[str, str], type[BaseAdapter]] = {}
        return cls._instance

    def register(
        self,
        input_fmts: list[str],
        output_fmt: str,
    ) -> Callable[[_AdapterT], _AdapterT]:
        """Decorator to register an adapter class for one or more input formats.

        Args:
            input_fmts: List of input format strings (e.g. ``["jpeg", "png"]``).
            output_fmt: Output format string (e.g. ``"pdf"``).

        Returns:
            The unmodified adapter class.
        """

        def decorator(cls: _AdapterT) -> _AdapterT:
            for fmt in input_fmts:
                self._registry[(fmt.lower(), output_fmt.lower())] = cls  # type: ignore[assignment]
            return cls

        return decorator

    def lookup(self, input_fmt: str, output_fmt: str) -> type[BaseAdapter]:
        """Look up the adapter for a given format pair.

        Args:
            input_fmt: Input format string.
            output_fmt: Output format string.

        Returns:
            The registered adapter class.

        Raises:
            UnsupportedConversionError: If no adapter is registered for the pair.
        """
        key = (input_fmt.lower(), output_fmt.lower())
        adapter = self._registry.get(key)
        if adapter is None:
            raise UnsupportedConversionError(input_fmt, output_fmt)
        return adapter

    def list_supported(self) -> list[tuple[str, str]]:
        """Return all registered (input_fmt, output_fmt) pairs.

        Returns:
            Sorted list of format-pair tuples.
        """
        return sorted(self._registry.keys())


# Module-level singleton
registry = ConversionRegistry()
