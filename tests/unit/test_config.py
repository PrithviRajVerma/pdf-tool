"""Unit tests for ConfigManager and config utilities."""

from __future__ import annotations

from pathlib import Path

from pdf_tool.utils.config import ConfigManager, coerce_value


def test_coerce_value():
    assert coerce_value("true", bool) is True
    assert coerce_value("false", bool) is False
    assert coerce_value("1", bool) is True
    assert coerce_value("0", bool) is False
    assert coerce_value("yes", bool) is True
    assert coerce_value("no", bool) is False

    assert coerce_value("150", int) == 150
    assert coerce_value("invalid", int) == "invalid"

    assert coerce_value("3.14", float) == 3.14
    assert coerce_value("invalid", float) == "invalid"

    # Inferred coercion
    assert coerce_value("true") is True
    assert coerce_value("false") is False
    assert coerce_value("42") == 42
    assert coerce_value("3.1415") == 3.1415
    assert coerce_value("hello") == "hello"


def test_config_manager_defaults(tmp_path: Path):
    cfg_file = tmp_path / "config.toml"
    mgr = ConfigManager(config_path=cfg_file)

    assert mgr.get("defaults.image_dpi") == 150
    assert mgr.get("defaults.compression_level") == "medium"
    assert mgr.get("defaults.ocr_language") == "eng"
    assert mgr.get("nonexistent.key", "fallback") == "fallback"
    assert mgr.config_file == cfg_file


def test_config_manager_set_and_save(tmp_path: Path):
    cfg_file = tmp_path / "config.toml"
    mgr = ConfigManager(config_path=cfg_file)

    mgr.set("defaults.image_dpi", "300")
    mgr.set("defaults.compression_level", "high")
    mgr.set("custom.flag", "true")
    mgr.save()

    assert cfg_file.exists()

    # Load from disk with a new instance
    mgr2 = ConfigManager(config_path=cfg_file)
    assert mgr2.get("defaults.image_dpi") == 300
    assert mgr2.get("defaults.compression_level") == "high"
    assert mgr2.get("custom.flag") is True


def test_config_manager_reset(tmp_path: Path):
    cfg_file = tmp_path / "config.toml"
    mgr = ConfigManager(config_path=cfg_file)

    mgr.set("defaults.image_dpi", 400)
    assert mgr.get("defaults.image_dpi") == 400

    # Reset single key
    mgr.reset("defaults.image_dpi")
    assert mgr.get("defaults.image_dpi") == 150

    # Custom key reset
    mgr.set("custom.temp", "value")
    assert mgr.get("custom.temp") == "value"
    mgr.reset("custom.temp")
    assert mgr.get("custom.temp") is None

    # Reset all
    mgr.set("defaults.ocr_language", "fra")
    mgr.reset()
    assert mgr.get("defaults.ocr_language") == "eng"


def test_config_manager_all(tmp_path: Path):
    cfg_file = tmp_path / "config.toml"
    mgr = ConfigManager(config_path=cfg_file)

    all_data = mgr.all()
    assert "defaults" in all_data
    assert "engines" in all_data
    assert all_data["defaults"]["image_dpi"] == 150
