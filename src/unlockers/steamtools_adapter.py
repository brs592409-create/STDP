"""SteamTools / Lua hook adapter for STDP."""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
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

    @staticmethod
    def find_steamtools_exe() -> Optional[Path]:
        """Detect SteamTools.exe location across Windows Registry, standard Program Files, AppData, and local paths."""
        # 1. Check Windows Registry (HKLM & HKCU)
        if sys.platform == "win32":
            try:
                import winreg
                reg_paths = [
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\SteamTools"),
                    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\SteamTools"),
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SteamTools"),
                    (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steamtools"),
                ]
                for root_key, subkey in reg_paths:
                    try:
                        with winreg.OpenKey(root_key, subkey) as key:
                            for val_name in ["InstallLocation", "DisplayIcon", "Path", "InstallPath"]:
                                try:
                                    val, _ = winreg.QueryValueEx(key, val_name)
                                    if val:
                                        p = Path(str(val).replace('"', '').strip())
                                        if p.is_dir() and (p / "SteamTools.exe").exists():
                                            return p / "SteamTools.exe"
                                        elif p.is_file() and p.name.lower() == "steamtools.exe" and p.exists():
                                            return p
                                except (FileNotFoundError, OSError):
                                    pass
                    except (FileNotFoundError, OSError):
                        pass
            except Exception as e:
                logger.debug(f"Registry lookup for SteamTools: {e}")

        # 2. Check standard filesystem paths
        env_pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
        env_pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        env_local = os.environ.get("LOCALAPPDATA", "")
        env_roaming = os.environ.get("APPDATA", "")

        candidates: List[Path] = [
            Path(env_pf86) / "SteamTools" / "SteamTools.exe",
            Path(env_pf) / "SteamTools" / "SteamTools.exe",
            Path(r"C:\Program Files (x86)\SteamTools\SteamTools.exe"),
            Path(r"C:\Program Files\SteamTools\SteamTools.exe"),
        ]
        if env_local:
            candidates.extend([
                Path(env_local) / "Programs" / "SteamTools" / "SteamTools.exe",
                Path(env_local) / "SteamTools" / "SteamTools.exe",
            ])
        if env_roaming:
            candidates.extend([
                Path(env_roaming) / "SteamTools" / "SteamTools.exe",
            ])

        # Home fallbacks
        home = Path.home()
        candidates.extend([
            home / "AppData" / "Local" / "Programs" / "SteamTools" / "SteamTools.exe",
            home / "AppData" / "Local" / "SteamTools" / "SteamTools.exe",
            home / "AppData" / "Roaming" / "SteamTools" / "SteamTools.exe",
        ])

        # Frozen and local directory fallbacks
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            candidates.extend([
                exe_dir / "SteamTools.exe",
                exe_dir / "bundled_installers" / "SteamTools.exe",
            ])

        project_root = Path(__file__).resolve().parent.parent.parent
        candidates.extend([
            project_root / "SteamTools.exe",
            project_root / "bundled_installers" / "SteamTools.exe",
        ])

        for c in candidates:
            try:
                if c and c.exists() and c.is_file():
                    return c
            except Exception:
                pass

        return None

    @staticmethod
    def is_steamtools_running() -> bool:
        """Check whether SteamTools.exe process is currently active."""
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    name = proc.info.get("name")
                    if name and name.lower() in ("steamtools.exe", "steamtools"):
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            logger.debug(f"Process check for SteamTools failed: {e}")
        return False

    @staticmethod
    def deploy_core_dll(steam_path: Union[Path, str]) -> bool:
        """Ensure Core.dll is deployed from SteamTools installation folder directly to Steam root."""
        sp = Path(steam_path)
        if not sp.exists():
            return False

        st_exe = SteamToolsAdapter.find_steamtools_exe()
        if not st_exe:
            return False

        st_dir = st_exe.parent
        core_src = st_dir / "Core.dll"
        if core_src.exists():
            try:
                target = sp / "Core.dll"
                if not target.exists() or target.stat().st_size != core_src.stat().st_size:
                    shutil.copy2(core_src, target)
                    logger.info(f"Deployed Core.dll to Steam root: {target}")
                return True
            except Exception as e:
                logger.warning(f"Could not deploy Core.dll to Steam directory: {e}")
        return False

    def is_installed(self, steam_path: Union[Path, str]) -> bool:
        """Check if SteamTools is installed, hook DLLs exist, or script directories are present."""
        if self.find_steamtools_exe() is not None:
            return True
        sp = Path(steam_path)
        if (sp / "Core.dll").exists() or (sp / "xinput1_4.dll").exists():
            return True
        for d in [sp / "config" / "st_scripts", sp / "st_scripts", sp / "config" / "stplug-in", sp / "stplug-in"]:
            if d.exists():
                return True
        appdata = os.environ.get("APPDATA")
        if appdata and (Path(appdata) / "SteamTools").exists():
            return True
        return False

    @staticmethod
    def get_bundled_installer() -> Optional[Path]:
        """Resolve bundled SteamTools st-setup installer across development and PyInstaller frozen runtime."""
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

    def _run_bundled_installer(self) -> bool:
        """Execute bundled SteamTools installer silently."""
        installer = self.get_bundled_installer()
        if not installer or not installer.exists():
            logger.warning("Bundled SteamTools installer st-setup-1.8.30.exe not found.")
            return False

        try:
            import subprocess
            logger.info(f"Running bundled SteamTools silent installer: {installer}")
            subprocess.run([str(installer), "/S"], timeout=30, check=False)
            logger.info("SteamTools silent installation completed via subprocess.")
            return True
        except OSError as os_err:
            if getattr(os_err, "winerror", None) == 740 or "740" in str(os_err):
                try:
                    import ctypes
                    logger.info("Requesting UAC elevation for SteamTools setup...")
                    ret = ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", str(installer), "/S", None, 0
                    )
                    if ret > 32:
                        logger.info("SteamTools silent installation launched with UAC elevation.")
                        return True
                    else:
                        logger.warning(f"ShellExecuteW returned code: {ret}")
                except Exception as uac_ex:
                    logger.warning(f"Failed to elevate installer: {uac_ex}")
            else:
                logger.warning(f"Could not execute bundled installer automatically: {os_err}")
        except Exception as ex:
            logger.warning(f"Could not execute bundled installer automatically: {ex}")
        return False

    def ensure_steamtools_running(self, steam_path: Optional[Union[Path, str]] = None) -> bool:
        """Ensure SteamTools is installed and active in background. Auto-installs and launches if needed."""
        import subprocess

        if self.is_steamtools_running():
            if steam_path:
                self.deploy_core_dll(steam_path)
            return True

        st_exe = self.find_steamtools_exe()

        # If not installed, try to run bundled installer
        if not st_exe:
            logger.info("SteamTools.exe not found on disk, running silent installer...")
            self._run_bundled_installer()
            time.sleep(2.0)
            st_exe = self.find_steamtools_exe()

        if not st_exe or not st_exe.exists():
            logger.warning("SteamTools could not be found or installed.")
            return False

        # Deploy Core.dll before starting
        if steam_path:
            self.deploy_core_dll(steam_path)

        # Launch SteamTools.exe in background
        logger.info(f"Starting SteamTools background hook engine: {st_exe}")
        try:
            if sys.platform == "win32":
                creation_flags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
                subprocess.Popen(
                    [str(st_exe)],
                    creationflags=creation_flags,
                    close_fds=True,
                )
            else:
                subprocess.Popen([str(st_exe)], close_fds=True)

            time.sleep(1.5)
            logger.info("SteamTools hook engine started successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to launch SteamTools.exe: {e}")
            return False

    @staticmethod
    def enable_autostart() -> bool:
        """Register SteamTools in Windows registry Run key so it starts automatically with Windows."""
        if sys.platform != "win32":
            return False
        st_exe = SteamToolsAdapter.find_steamtools_exe()
        if not st_exe or not st_exe.exists():
            return False
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, "SteamTools", 0, winreg.REG_SZ, f'"{st_exe}"')
            logger.info(f"SteamTools registered to Windows startup: {st_exe}")
            return True
        except Exception as e:
            logger.warning(f"Could not register SteamTools to startup: {e}")
            return False

    def install_hook(self, steam_path: Union[Path, str]) -> bool:
        """Create necessary st_scripts directories, deploy Core.dll, enable startup, and ensure SteamTools is running."""
        try:
            # 1. Ensure scripts directories
            for d in self._get_scripts_dirs(steam_path):
                d.mkdir(parents=True, exist_ok=True)
            logger.info("Initialized SteamTools scripts directories.")

            # 2. Run bundled silent installer if not installed
            if not self.find_steamtools_exe():
                self._run_bundled_installer()

            # 3. Deploy Core.dll
            self.deploy_core_dll(steam_path)

            # 4. Register SteamTools to autostart on Windows boot
            self.enable_autostart()

            # 5. Ensure SteamTools background process is active
            self.ensure_steamtools_running(steam_path)

            return True
        except Exception as e:
            logger.error(f"Failed to initialize SteamTools hook: {e}")
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
        """Write <appid>.lua script into config/st_scripts/ and st_scripts/ and ensure SteamTools is running."""
        try:
            self.install_hook(steam_path)

            # Ensure SteamTools is active before injecting and restarting Steam
            self.ensure_steamtools_running(steam_path)

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

            # Merge any custom Lua script with guaranteed manifest IDs, depot keys, and addappids
            final_content = KeyInjector.merge_or_generate_lua_script(app_info, custom_lua_content)

            # Write to all script directories for 100% compatibility
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
