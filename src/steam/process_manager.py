"""Steam process controller, graceful shutdown, restart, and URI triggering."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Union
import psutil

from src.core.logger import get_logger
from src.steam.detector import steam_detector

logger = get_logger("steam.process_manager")


class SteamProcessManager:
    """Manages Steam execution lifecycle, graceful shutdowns, and custom protocol triggers."""

    @staticmethod
    def get_steam_process() -> Optional[psutil.Process]:
        """Find the active steam.exe process if running."""
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info["name"]
                if name and name.lower() == "steam.exe":
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    @staticmethod
    def is_running() -> bool:
        """Check whether Steam process is currently active."""
        return SteamProcessManager.get_steam_process() is not None

    @staticmethod
    def get_pid() -> Optional[int]:
        """Return PID of active Steam process, or None."""
        proc = SteamProcessManager.get_steam_process()
        return proc.pid if proc else None

    @staticmethod
    def shutdown_steam(
        steam_path: Optional[Union[Path, str]] = None,
        timeout_seconds: int = 15,
        force_kill_on_timeout: bool = False,
    ) -> bool:
        """Gracefully shut down Steam using steam.exe -shutdown with timeout polling."""
        if not SteamProcessManager.is_running():
            logger.info("Steam is already stopped.")
            return True

        resolved_steam_path = (
            Path(steam_path) if steam_path else steam_detector.find_steam_path()
        )
        steam_exe = resolved_steam_path / "steam.exe" if resolved_steam_path else None

        logger.info("Sending graceful shutdown request to Steam (-shutdown)...")
        try:
            if steam_exe and steam_exe.exists():
                subprocess.run(
                    [str(steam_exe), "-shutdown"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                # Fallback to calling 'steam -shutdown' directly
                subprocess.run(
                    ["steam", "-shutdown"],
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
        except Exception as e:
            logger.warning(f"Failed to execute steam -shutdown command: {e}")

        # Poll for process termination
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if not SteamProcessManager.is_running():
                time.sleep(0.6)  # Grace period for Windows to fully release file locks on config.vdf
                logger.info("Steam shut down successfully and file locks released.")
                return True
            time.sleep(0.5)

        logger.warning(f"Steam did not shut down within {timeout_seconds} seconds.")

        # Fallback force kill if requested
        if force_kill_on_timeout:
            logger.warning("Forcefully terminating Steam process tree...")
            proc = SteamProcessManager.get_steam_process()
            if proc:
                try:
                    for child in proc.children(recursive=True):
                        child.kill()
                    proc.kill()
                    proc.wait(timeout=5)
                    logger.info("Steam process was forcefully terminated.")
                    return True
                except Exception as e:
                    logger.error(f"Error forcefully terminating Steam: {e}")
                    return False

        return False

    @staticmethod
    def start_steam(
        steam_path: Optional[Union[Path, str]] = None,
        extra_args: Optional[List[str]] = None,
    ) -> bool:
        """Start Steam client executable."""
        resolved_path = (
            Path(steam_path) if steam_path else steam_detector.find_steam_path()
        )
        if not resolved_path or not (resolved_path / "steam.exe").exists():
            logger.error("Cannot start Steam: steam.exe not found.")
            return False

        steam_exe = resolved_path / "steam.exe"
        cmd = [str(steam_exe)]
        if extra_args:
            cmd.extend(extra_args)

        logger.info(f"Starting Steam: {cmd}")
        try:
            if sys.platform == "win32":
                # Launch detached without blocking
                creation_flags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
                )
                subprocess.Popen(
                    cmd,
                    creationflags=creation_flags,
                    close_fds=True,
                )
            else:
                subprocess.Popen(cmd, close_fds=True)
            return True
        except Exception as e:
            logger.error(f"Failed to launch Steam: {e}")
            return False

    @staticmethod
    def restart_steam(
        steam_path: Optional[Union[Path, str]] = None,
        timeout_seconds: int = 15,
        extra_args: Optional[List[str]] = None,
    ) -> bool:
        """Shut down and start Steam again."""
        logger.info("Restarting Steam...")
        shutdown_ok = SteamProcessManager.shutdown_steam(
            steam_path=steam_path, timeout_seconds=timeout_seconds, force_kill_on_timeout=True
        )
        if not shutdown_ok:
            logger.warning("Could not stop Steam cleanly during restart attempt.")

        time.sleep(1.0)
        return SteamProcessManager.start_steam(steam_path=steam_path, extra_args=extra_args)

    @staticmethod
    def trigger_nav_game(app_id: int) -> bool:
        """Open and focus the game in Steam Library without triggering purchase store modal."""
        uri = f"steam://nav/games/details/{app_id}"
        logger.info(f"Triggering Steam library navigation URI: {uri}")
        try:
            if sys.platform == "win32":
                os.startfile(uri)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", uri])
            return True
        except Exception as e:
            logger.error(f"Failed to trigger library navigation URI for AppID {app_id}: {e}")
            return False

    @staticmethod
    def trigger_install(app_id: int) -> bool:
        """Trigger steam://install/<app_id> to open the game's install dialog in Steam."""
        uri = f"steam://install/{app_id}"
        logger.info(f"Triggering Steam install URI: {uri}")
        try:
            if sys.platform == "win32":
                os.startfile(uri)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", uri])
            return True
        except Exception as e:
            logger.error(f"Failed to trigger install URI for AppID {app_id}: {e}")
            return False

    @staticmethod
    def trigger_validate(app_id: int) -> bool:
        """Trigger steam://validate/<app_id> protocol to verify game files."""
        uri = f"steam://validate/{app_id}"
        logger.info(f"Triggering Steam validate URI: {uri}")
        try:
            if sys.platform == "win32":
                os.startfile(uri)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", uri])
            return True
        except Exception as e:
            logger.error(f"Failed to trigger validate URI for AppID {app_id}: {e}")
            return False

    @staticmethod
    def wait_until_ready(
        timeout_seconds: int = 30,
        poll_interval: float = 1.0,
    ) -> bool:
        """Wait until Steam is fully initialized by checking for steamwebhelper.exe.

        Steam's UI and plugin system (including SteamTools hook) are only
        operational once steamwebhelper.exe is running. This method polls for
        that process, giving the hook enough time to load Lua scripts and
        register owned games before any steam:// URI commands are triggered.

        Returns True if Steam became ready within the timeout, False otherwise.
        """
        start_time = time.time()
        webhelper_seen = False

        logger.info(f"Waiting up to {timeout_seconds}s for Steam to fully initialize (steamwebhelper)...")

        while time.time() - start_time < timeout_seconds:
            # First check that steam.exe itself is still running
            if not SteamProcessManager.is_running():
                time.sleep(poll_interval)
                continue

            # Look for steamwebhelper.exe which signals the UI layer is up
            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info.get("name", "")
                    if name and name.lower() == "steamwebhelper.exe":
                        webhelper_seen = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue

            if webhelper_seen:
                # Give an extra grace period for SteamTools hook to load Lua scripts
                # after the UI layer is up
                grace_seconds = 5.0
                logger.info(
                    f"steamwebhelper.exe detected. Waiting {grace_seconds}s grace period "
                    f"for SteamTools hook to initialize..."
                )
                time.sleep(grace_seconds)
                logger.info("Steam is considered fully ready.")
                return True

            time.sleep(poll_interval)

        logger.warning(f"Steam did not become fully ready within {timeout_seconds} seconds.")
        return False


# Global singleton instance
steam_process_manager = SteamProcessManager()
