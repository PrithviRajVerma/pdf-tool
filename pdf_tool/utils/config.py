"""User configuration manager backed by ~/.pdf-tool/config.toml."""

from __future__ import annotations

import copy
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

_CONFIG_DIR = Path.home() / ".pdf-tool"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"

_DEFAULTS: dict[str, Any] = {
    "defaults": {
        "output_dir": "",
        "compression_level": "medium",
        "image_dpi": 150,
        "ocr_language": "eng",
        "markdown_renderer": "weasyprint",
        "quality": "medium",
    },
    "engines": {
        "libreoffice_path": "",
        "ghostscript_path": "",
        "tesseract_path": "",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning a new dict."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def coerce_value(raw: str, expected_type: type | None = None) -> Any:
    """Coerce a string value into an appropriate typed representation."""
    if expected_type is bool or (
        expected_type is None and raw.lower() in ("true", "false", "yes", "no")
    ):
        return raw.lower() in ("true", "1", "yes")

    if expected_type is int:
        try:
            return int(raw)
        except ValueError:
            pass

    if expected_type is float:
        try:
            return float(raw)
        except ValueError:
            pass

    if expected_type is None:
        try:
            return int(raw)
        except ValueError:
            pass
        try:
            return float(raw)
        except ValueError:
            pass

    return raw


class ConfigManager:
    """Manages persistent user configuration stored in ``~/.pdf-tool/config.toml``.

    Config keys use dot-notation, e.g. ``"defaults.image_dpi"`` or ``"engines.ghostscript_path"``.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_file = config_path or _CONFIG_FILE
        self._data: dict[str, Any] = _deep_merge(_DEFAULTS, self._load_from_disk())

    @property
    def config_file(self) -> Path:
        """Return the path to the configuration file."""
        return self._config_file

    def _load_from_disk(self) -> dict[str, Any]:
        if not self._config_file.exists():
            return {}
        try:
            with self._config_file.open("rb") as fh:
                return tomllib.load(fh)
        except Exception:
            return {}

    def _resolve(self, key: str, create: bool = True) -> tuple[dict, str]:
        """Resolve a dot-notation key to (parent_dict, leaf_key)."""
        parts = key.split(".")
        node: dict[str, Any] = self._data
        for part in parts[:-1]:
            if create:
                node = node.setdefault(part, {})
            else:
                if part not in node or not isinstance(node[part], dict):
                    raise KeyError(key)
                node = node[part]
        return node, parts[-1]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by dot-notation key.

        Args:
            key: Dot-notation key, e.g. ``"defaults.image_dpi"``.
            default: Value to return if the key is not found.

        Returns:
            The config value, or *default*.
        """
        try:
            parent, leaf = self._resolve(key, create=False)
            return parent.get(leaf, default)
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Set a config value by dot-notation key.

        Args:
            key: Dot-notation key.
            value: New value to set.
        """
        # Look up expected type from defaults if present
        expected_type = None
        default_val = self.get_default(key)
        if default_val is not None:
            expected_type = type(default_val)

        if isinstance(value, str):
            coerced_value = coerce_value(value, expected_type)
        else:
            coerced_value = value

        parent, leaf = self._resolve(key, create=True)
        parent[leaf] = coerced_value

    def get_default(self, key: str) -> Any:
        """Retrieve the default value for a dot-notation key if defined."""
        parts = key.split(".")
        node: Any = _DEFAULTS
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return None
        return node

    def reset(self, key: str | None = None) -> None:
        """Reset configuration to defaults.

        Args:
            key: Dot-notation key to reset. If None, resets all settings.
        """
        if key is None:
            self._data = copy.deepcopy(_DEFAULTS)
        else:
            default_val = self.get_default(key)
            if default_val is not None:
                parent, leaf = self._resolve(key, create=True)
                parent[leaf] = copy.deepcopy(default_val)
            else:
                try:
                    parent, leaf = self._resolve(key, create=False)
                    parent.pop(leaf, None)
                except (KeyError, TypeError):
                    pass

    def all(self) -> dict[str, Any]:
        """Return a copy of the full config dict."""
        return copy.deepcopy(self._data)

    def save(self) -> None:
        """Persist the current config to the configured TOML file."""
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        with self._config_file.open("wb") as fh:
            tomli_w.dump(self._data, fh)


_GLOBAL_CONFIG: ConfigManager | None = None


def get_config() -> ConfigManager:
    """Return the global ConfigManager instance."""
    global _GLOBAL_CONFIG
    if _GLOBAL_CONFIG is None:
        _GLOBAL_CONFIG = ConfigManager()
    return _GLOBAL_CONFIG
