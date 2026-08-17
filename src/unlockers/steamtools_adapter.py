"""SteamTools / Lua hook adapter for STDP."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path
from typing import List, Optional, Union

from src.core.logger import get_logger
from src.core.models import AppInfo, GamePackage
from src.steam.key_injector import KeyInjector
from src.unlockers.base import UnlockerAdapter

logger = get_logger("unlockers.steamtools")


class SteamToolsAdapter(UnlockerAdapter):
    """Adapter for managing SteamTools Lua scripts across all known hook paths."""

    @property
    def name(self) -> str:
        return "SteamTools (Lua Kanca)"

    @property
    def identifier(self) -> str:
        return "steamtools"

    @property
    def description(self) -> str:
        return "Yerleşik Lua kanca motoru. st_scripts, lua ve %APPDATA%/SteamTools betikleri ile çalışır."

    def _get_scripts_dirs(self, steam_path: Union[Path, str]) -> List[Path]:
        """Resolve all primary and fallback Lua script directories across SteamTools and OpenSteamTool."""
        sp = Path(steam_path)
        dirs = [
            sp / "config" / "stplug-in",
            sp / "stplug-in",
            sp / "config" / "st_scripts",
            sp / "st_scripts",
            sp / "lua",
            sp / "steamtools" / "lua",
            sp / "plugins",
        ]
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(Path(appdata) / "SteamTools" / "scripts")
        else:
            dirs.append(Path.home() / "AppData" / "Roaming" / "SteamTools" / "scripts")
        return dirs

    def is_installed(self, steam_path: Union[Path, str]) -> bool:
        """Check if any hook script directory is present in the target Steam installation."""
        sp = Path(steam_path)
        steam_subdirs = [
            sp / "config" / "stplug-in",
            sp / "stplug-in",
            sp / "config" / "st_scripts",
            sp / "st_scripts",
            sp / "lua",
            sp / "steamtools" / "lua",
            sp / "plugins",
        ]
        return any(d.exists() for d in steam_subdirs)

    @staticmethod
    def get_bundled_installer() -> Optional[Path]:
        """Resolve bundled SteamTools st-setup installer across development and PyInstaller frozen runtime."""
        import sys
        candidates: List[Path] = []
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "bundled_installers" / "st-setup-1.8.30.exe")
            candidates.append(Path(sys._MEIPASS) / "st-setup-1.8.30.exe")

        project_root = Path(__file__).resolve().parent.parent.parent
        candidates.append(project_root / "bundled_installers" / "st-setup-1.8.30.exe")
        candidates.append(project_root / "st-setup-1.8.30.exe")

        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates.append(exe_dir / "bundled_installers" / "st-setup-1.8.30.exe")
            candidates.append(exe_dir / "st-setup-1.8.30.exe")

        for c in candidates:
            if c.exists():
                return c
        return None

    def install_hook(self, steam_path: Union[Path, str]) -> bool:
        """Create necessary st_scripts directories in Steam and execute bundled installer if present."""
        try:
            # 1. Ensure scripts directories
            for d in self._get_scripts_dirs(steam_path):
                d.mkdir(parents=True, exist_ok=True)
            logger.info("Initialized SteamTools scripts directories.")

            # 2. Run bundled silent installer if available
            installer = self.get_bundled_installer()
            if installer and installer.exists():
                try:
                    import subprocess
                    logger.info(f"Running bundled SteamTools silent installer: {installer}")
                    subprocess.run([str(installer), "/S"], timeout=30, check=False)
                    logger.info("SteamTools silent installation completed via subprocess.")
                except OSError as os_err:
                    # If WinError 740 (Elevation required), launch with Windows UAC elevation
                    if getattr(os_err, "winerror", None) == 740 or "740" in str(os_err):
                        try:
                            import ctypes
                            logger.info("Requesting UAC elevation for SteamTools setup...")
                            # ShellExecuteW: hwnd, verb, file, params, dir, show
                            ret = ctypes.windll.shell32.ShellExecuteW(
                                None, "runas", str(installer), "/S", None, 0
                            )
                            if ret > 32:
                                logger.info("SteamTools silent installation launched with UAC elevation.")
                            else:
                                logger.warning(f"ShellExecuteW returned code: {ret}")
                        except Exception as uac_ex:
                            logger.warning(f"Failed to elevate installer: {uac_ex}")
                    else:
                        logger.warning(f"Could not execute bundled installer automatically: {os_err}")
                except Exception as ex:
                    logger.warning(f"Could not execute bundled installer automatically: {ex}")

            return True
        except Exception as e:
            logger.error(f"Failed to initialize SteamTools scripts directory: {e}")
            return False

    def uninstall_hook(self, steam_path: Union[Path, str]) -> bool:
        """Safely backup and clear the st_scripts directories."""
        try:
            for scripts_dir in self._get_scripts_dirs(steam_path):
                if scripts_dir.exists():
                    backup_dir = scripts_dir.parent / f"{scripts_dir.name}_backup"
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)
                    shutil.copytree(scripts_dir, backup_dir)
                    shutil.rmtree(scripts_dir)
                    logger.info(f"SteamTools scripts backed up to {backup_dir} and removed.")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall SteamTools hook: {e}")
            return False

    def inject_game(
        self,
        steam_path: Union[Path, str],
        app_info: AppInfo,
        package: Optional[GamePackage] = None,
    ) -> bool:
        """Write <appid>.lua script into config/st_scripts/ and st_scripts/."""
        try:
            self.install_hook(steam_path)

            # Check if package contains a custom Lua script
            custom_lua_content: Optional[str] = None
            if package and package.lua_scripts:
                expected_name = f"{app_info.app_id}.lua"
                if expected_name in package.lua_scripts:
                    custom_lua_content = package.lua_scripts[expected_name]
                elif package.lua_scripts:
                    custom_lua_content = next(iter(package.lua_scripts.values()))

            if not custom_lua_content and app_info.lua_content:
                custom_lua_content = app_info.lua_content

            if custom_lua_content:
                final_content = custom_lua_content.strip() + "\n"
            else:
                final_content = KeyInjector.generate_lua_script(app_info)

            # Write to both script directories for 100% compatibility
            for scripts_dir in self._get_scripts_dirs(steam_path):
                scripts_dir.mkdir(parents=True, exist_ok=True)
                target_lua = scripts_dir / f"{app_info.app_id}.lua"
                target_lua.write_text(final_content, encoding="utf-8")
                logger.info(f"Wrote SteamTools Lua script: {target_lua}")

            return True
        except Exception as e:
            logger.error(f"Failed to inject Lua script for AppID {app_info.app_id}: {e}")
            return False

    def remove_game(self, steam_path: Union[Path, str], app_id: int) -> bool:
        """Remove <appid>.lua script from all directories."""
        try:
            for scripts_dir in self._get_scripts_dirs(steam_path):
                target_lua = scripts_dir / f"{app_id}.lua"
                if target_lua.exists():
                    target_lua.unlink()
                    logger.info(f"Removed Lua script for AppID {app_id}: {target_lua}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove Lua script for AppID {app_id}: {e}")
            return False

    def list_injected_games(self, steam_path: Union[Path, str]) -> List[int]:
        """List all AppIDs extracted from *.lua files."""
        app_ids: set[int] = set()
        for scripts_dir in self._get_scripts_dirs(steam_path):
            if not scripts_dir.exists():
                continue
            for lua_file in scripts_dir.glob("*.lua"):
                stem = lua_file.stem
                if stem.isdigit():
                    app_ids.add(int(stem))
                else:
                    try:
                        content = lua_file.read_text(encoding="utf-8")
                        for match in re.finditer(r"addappid\s*\(\s*(\d+)", content, re.IGNORECASE):
                            app_ids.add(int(match.group(1)))
                    except Exception:
                        pass

        return sorted(list(app_ids))
