"""Unit tests for config manager."""

import json
from pathlib import Path
from src.core.config import AppConfig, ConfigManager


def test_config_manager_default(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_path=cfg_file)

    assert cfg_file.exists()
    assert mgr.config.active_unlocker == "steamtools"
    assert mgr.config.auto_shutdown_steam is True
    assert mgr.config.depotbox_api_url == "https://depotbox.org"


def test_config_manager_update(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    mgr = ConfigManager(config_path=cfg_file)

    mgr.update(active_unlocker="greenluma", auto_shutdown_steam=False)
    assert mgr.config.active_unlocker == "greenluma"
    assert mgr.config.auto_shutdown_steam is False

    # Reload from disk
    new_mgr = ConfigManager(config_path=cfg_file)
    assert new_mgr.config.active_unlocker == "greenluma"
    assert new_mgr.config.auto_shutdown_steam is False


def test_config_manager_corrupted_file(tmp_path: Path):
    cfg_file = tmp_path / "corrupted_config.json"
    cfg_file.write_text("{invalid json", encoding="utf-8")

    mgr = ConfigManager(config_path=cfg_file)
    assert mgr.config.active_unlocker == "steamtools"
