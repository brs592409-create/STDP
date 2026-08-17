"""Configuration manager for STDP."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    """Application configuration schema."""

    steam_path: Optional[str] = None
    selected_library_path: Optional[str] = None
    active_unlocker: str = "steamtools"  # "steamtools" or "greenluma"
    auto_shutdown_steam: bool = True
    auto_restart_steam: bool = True
    depotbox_api_url: str = "https://depotbox.org"
    depotbox_timeout_seconds: int = 15
    theme: str = "steam_dark"
    log_level: str = "INFO"
    downloads_dir: Optional[str] = None
    onlinefix_login_prompt_shown: bool = False


def get_user_data_dir() -> Path:
    """Return persistent, writable directory for application files (config, logs).
    
    If running portable (writable local directory), uses the application directory.
    If installed in a protected location (like Program Files), falls back to %LOCALAPPDATA%/STDP.
    """
    if getattr(sys, "frozen", False):
        local_dir = Path(sys.executable).resolve().parent
    else:
        local_dir = Path(__file__).resolve().parent.parent.parent

    # Test if local_dir is writable
    test_file = local_dir / ".stdp_write_test"
    try:
        test_file.touch()
        test_file.unlink()
        return local_dir
    except (PermissionError, OSError):
        pass

    # Protected location fallback: %LOCALAPPDATA%\STDP or %APPDATA%\STDP
    local_appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if local_appdata:
        app_dir = Path(local_appdata) / "STDP"
    else:
        app_dir = Path.home() / ".stdp"

    try:
        app_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return app_dir


def get_app_dir() -> Path:
    """Return persistent directory for application files (config, logs)."""
    return get_user_data_dir()


class ConfigManager:
    """Handles loading, saving, and updating application configuration."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = get_user_data_dir() / "config.json"

        self._config: AppConfig = AppConfig()
        self.load()

    @property
    def config(self) -> AppConfig:
        """Access current active configuration."""
        return self._config

    def load(self) -> AppConfig:
        """Load configuration from JSON file or create with defaults if missing."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._config = AppConfig.model_validate(data)
            except Exception:
                # If corrupted or unreadable, fallback to default and persist
                self._config = AppConfig()
                self.save()
        else:
            # Check for bundled default config in PyInstaller MEIPASS if available
            bundled_cfg = None
            if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
                bundled_cfg = Path(sys._MEIPASS) / "config.json"

            if bundled_cfg and bundled_cfg.exists():
                try:
                    with open(bundled_cfg, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._config = AppConfig.model_validate(data)
                except Exception:
                    self._config = AppConfig()
            else:
                self._config = AppConfig()

            try:
                self.save()
            except Exception:
                pass

        # Validate that steam_path actually exists if set; if not, reset to None for dynamic detection
        if self._config.steam_path and not Path(self._config.steam_path).exists():
            self._config.steam_path = None

        return self._config

    def save(self) -> None:
        """Persist current configuration to JSON file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config.model_dump(), f, indent=2, ensure_ascii=False)

    def update(self, **kwargs: Any) -> AppConfig:
        """Update one or more config fields and save immediately."""
        current_data = self._config.model_dump()
        current_data.update(kwargs)
        self._config = AppConfig.model_validate(current_data)
        self.save()
        return self._config

    def reset_to_defaults(self) -> AppConfig:
        """Reset configuration back to factory default values."""
        self._config = AppConfig()
        self.save()
        return self._config


# Global singleton instance for easy import across the application
config_manager = ConfigManager()
