"""Steam installation, library folders, and system health detector."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional
import psutil

from src.core.logger import get_logger
from src.core.models import LibraryFolder, SystemHealth
from src.steam.vdf_parser import parse_vdf_file

logger = get_logger("steam.detector")


class SteamDetector:
    """Detects Steam installation directory, multi-drive library folders, and system health."""

    COMMON_PATHS = [
        r"C:\Program Files (x86)\Steam",
        r"C:\Program Files\Steam",
        r"D:\Steam",
        r"D:\SteamLibrary",
        r"E:\Steam",
        r"E:\SteamLibrary",
    ]

    def __init__(self, override_steam_path: Optional[Path | str] = None) -> None:
        self.override_steam_path = Path(override_steam_path) if override_steam_path else None

    def find_steam_path(self) -> Optional[Path]:
        """Detect Steam installation path via Registry, overrides, or common fallback paths."""
        if self.override_steam_path and self.override_steam_path.exists():
            return self.override_steam_path

        # 1. Windows Registry detection
        if sys.platform == "win32":
            try:
                import winreg

                # Check HKCU
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                        val, _ = winreg.QueryValueEx(key, "SteamPath")
                        if val:
                            p = Path(val)
                            if p.exists():
                                return p
                except (FileNotFoundError, OSError):
                    pass

                # Check HKLM 64-bit / 32-bit
                for subkey in [r"SOFTWARE\WOW6432Node\Valve\Steam", r"SOFTWARE\Valve\Steam"]:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey) as key:
                            val, _ = winreg.QueryValueEx(key, "InstallPath")
                            if val:
                                p = Path(val)
                                if p.exists():
                                    return p
                    except (FileNotFoundError, OSError):
                        pass
            except Exception as e:
                logger.warning(f"Error reading Steam registry: {e}")

        # 2. Check common paths on disk
        for p_str in self.COMMON_PATHS:
            p = Path(p_str)
            if p.exists() and (p / "steam.exe").exists():
                return p

        logger.warning("Steam installation directory could not be automatically detected.")
        return None

    def get_library_folders(self, steam_path: Optional[Path] = None) -> List[LibraryFolder]:
        """Read and parse libraryfolders.vdf across all drives to return available libraries."""
        base_steam = steam_path or self.find_steam_path()
        if not base_steam or not base_steam.exists():
            return []

        # Find libraryfolders.vdf location
        vdf_candidates = [
            base_steam / "steamapps" / "libraryfolders.vdf",
            base_steam / "config" / "libraryfolders.vdf",
        ]

        vdf_path: Optional[Path] = None
        for candidate in vdf_candidates:
            if candidate.exists():
                vdf_path = candidate
                break

        folders: List[LibraryFolder] = []

        # Always include the base Steam installation folder as default (folder 0) if valid
        base_steamapps = base_steam / "steamapps"
        if base_steamapps.exists() or base_steam.exists():
            total_b, free_b = self._get_disk_space(base_steam)
            folders.append(
                LibraryFolder(
                    folder_id=0,
                    path=base_steam,
                    label="Steam Root",
                    total_bytes=total_b,
                    free_bytes=free_b,
                    apps={},
                    mounted=True,
                )
            )

        if not vdf_path:
            return folders

        try:
            data = parse_vdf_file(vdf_path)
            lib_data = data.get("libraryfolders") or data.get("LibraryFolders") or {}

            for key, val in lib_data.items():
                if isinstance(val, dict):
                    # Modern format: "1" -> {"path": "D:\\SteamLibrary", "label": "", "apps": {...}}
                    try:
                        folder_id = int(key)
                    except ValueError:
                        folder_id = len(folders)

                    p_str = val.get("path")
                    if not p_str:
                        continue
                    folder_path = Path(p_str)

                    # Check apps mapping
                    raw_apps = val.get("apps", {})
                    apps_map: Dict[int, int] = {}
                    if isinstance(raw_apps, dict):
                        for app_k, size_v in raw_apps.items():
                            try:
                                apps_map[int(app_k)] = int(size_v)
                            except (ValueError, TypeError):
                                pass

                    total_b, free_b = self._get_disk_space(folder_path)
                    mounted = folder_path.exists()

                    # Avoid duplicate if matches base steam
                    if any(f.path.resolve() == folder_path.resolve() for f in folders):
                        # Update existing base entry with apps and label
                        for f in folders:
                            if f.path.resolve() == folder_path.resolve():
                                f.apps = apps_map
                                f.label = val.get("label", "") or f.label
                                f.folder_id = folder_id
                        continue

                    folders.append(
                        LibraryFolder(
                            folder_id=folder_id,
                            path=folder_path,
                            label=val.get("label", ""),
                            total_bytes=total_b,
                            free_bytes=free_b,
                            apps=apps_map,
                            mounted=mounted,
                        )
                    )
                elif isinstance(val, str) and key.isdigit():
                    # Legacy format: "1" -> "D:\\SteamLibrary"
                    folder_id = int(key)
                    folder_path = Path(val)
                    total_b, free_b = self._get_disk_space(folder_path)
                    mounted = folder_path.exists()

                    if not any(f.path.resolve() == folder_path.resolve() for f in folders):
                        folders.append(
                            LibraryFolder(
                                folder_id=folder_id,
                                path=folder_path,
                                label="",
                                total_bytes=total_b,
                                free_bytes=free_b,
                                apps={},
                                mounted=mounted,
                            )
                        )
        except Exception as e:
            logger.error(f"Failed to parse library folders from {vdf_path}: {e}")

        return folders

    def _get_disk_space(self, path: Path) -> tuple[int, int]:
        """Get (total_bytes, free_bytes) for the drive containing path."""
        try:
            if path.exists():
                usage = shutil.disk_usage(path)
                return usage.total, usage.free
            # If path doesn't exist yet, check drive root
            drive = path.drive or (path.parts[0] if path.parts else "C:\\")
            usage = shutil.disk_usage(drive)
            return usage.total, usage.free
        except Exception:
            return 0, 0

    def is_admin(self) -> bool:
        """Check if current process has Administrator privileges on Windows."""
        if sys.platform != "win32":
            return os.geteuid() == 0 if hasattr(os, "geteuid") else False
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def is_steam_running(self) -> tuple[bool, Optional[int]]:
        """Check if steam.exe process is currently active."""
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info["name"]
                if name and name.lower() == "steam.exe":
                    return True, proc.info["pid"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False, None

    def check_system_health(self) -> SystemHealth:
        """Run complete health check on Steam environment, permissions, and paths."""
        issues: List[str] = []
        steam_path = self.find_steam_path()

        steam_installed = steam_path is not None and steam_path.exists()
        if not steam_installed:
            issues.append("Steam kurulum dizini bulunamadı.")

        depotcache_writable = False
        if steam_installed and steam_path:
            depotcache_dir = steam_path / "depotcache"
            try:
                depotcache_dir.mkdir(parents=True, exist_ok=True)
                test_file = depotcache_dir / ".stdp_write_test"
                test_file.write_text("test", encoding="utf-8")
                test_file.unlink()
                depotcache_writable = True
            except Exception as e:
                issues.append(f"Depotcache klasörüne yazma izni yok: {e}")

        steam_running, steam_pid = self.is_steam_running()
        admin_status = self.is_admin()
        libraries = self.get_library_folders(steam_path) if steam_installed else []

        # Check unlocker and hook status
        hook_installed = False
        unlocker_installed = False
        unlocker_running = False

        try:
            from src.unlockers.steamtools_adapter import SteamToolsAdapter
            st_exe = SteamToolsAdapter.find_steamtools_exe()
            unlocker_installed = st_exe is not None
            unlocker_running = SteamToolsAdapter.is_steamtools_running()

            if steam_installed and steam_path:
                core_dll = steam_path / "Core.dll"
                xinput_dll = steam_path / "xinput1_4.dll"
                st_scripts = steam_path / "config" / "st_scripts"
                applist = steam_path / "AppList"
                hook_installed = unlocker_installed or core_dll.exists() or xinput_dll.exists() or st_scripts.exists() or applist.exists()

            if not unlocker_installed and not hook_installed:
                issues.append("SteamTools kilit motoru kurulu değil. Oyunların 'Lisans Yok' hatası vermemesi için SteamTools kurulmalıdır.")
            elif not unlocker_running:
                issues.append("SteamTools kilit motoru arka planda çalışmıyor. 'Lisans Yok' hatası almamak için SteamTools açık olmalıdır.")
        except Exception as e:
            logger.debug(f"Unlocker health check error: {e}")

        return SystemHealth(
            steam_installed=steam_installed,
            steam_path=steam_path,
            steam_running=steam_running,
            steam_pid=steam_pid,
            is_admin=admin_status,
            depotcache_writable=depotcache_writable,
            libraries_found=libraries,
            active_hook_installed=hook_installed,
            unlocker_installed=unlocker_installed,
            unlocker_running=unlocker_running,
            issues=issues,
        )


# Global singleton instance
steam_detector = SteamDetector()
