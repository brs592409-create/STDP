"""Background QThread workers for non-blocking UI operations."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union
from PyQt6.QtCore import QThread, pyqtSignal

from src.core.config import config_manager
from src.core.logger import get_logger
from src.core.models import AppInfo, GamePackage, SystemHealth
from src.depotbox.client import depotbox_client
from src.depotbox.downloader import manifest_downloader
from src.depotbox.extractor import archive_extractor
from src.steam.acf_builder import ACFBuilder
from src.steam.detector import steam_detector
from src.steam.key_injector import KeyInjector
from src.steam.process_manager import SteamProcessManager
from src.unlockers.factory import get_unlocker

logger = get_logger("ui.workers")


class SearchWorker(QThread):
    """Asynchronous search worker."""

    results_ready = pyqtSignal(list)  # List[AppInfo]
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str) -> None:
        super().__init__()
        self.query = query

    def run(self) -> None:
        try:
            results = depotbox_client.search(self.query)
            self.results_ready.emit(results)
        except Exception as e:
            logger.error(f"Search worker error: {e}")
            self.error_occurred.emit(str(e))


class PackageImportWorker(QThread):
    """Worker for parsing dropped archives and files."""

    package_ready = pyqtSignal(object)  # GamePackage
    error_occurred = pyqtSignal(str)

    def __init__(self, file_path: Union[Path, str]) -> None:
        super().__init__()
        self.file_path = file_path

    def run(self) -> None:
        try:
            pkg = archive_extractor.extract_package(self.file_path)
            self.package_ready.emit(pkg)
        except Exception as e:
            logger.error(f"Archive extraction worker error: {e}")
            self.error_occurred.emit(str(e))


class InjectGameWorker(QThread):
    """End-to-end game manifest download, ACF generation, config key injection, and hook injection worker."""

    progress = pyqtSignal(str, int)  # (status_message, percent 0-100)
    finished = pyqtSignal(bool, str)  # (success, message)

    def __init__(
        self,
        app_info: AppInfo,
        target_library_path: Path,
        package: Optional[GamePackage] = None,
        ready_to_install: bool = True,
    ) -> None:
        super().__init__()
        self.app_info = app_info
        self.target_library_path = target_library_path
        self.package = package
        self.ready_to_install = ready_to_install

    def run(self) -> None:
        cfg = config_manager.config
        steam_path = (
            Path(cfg.steam_path)
            if cfg.steam_path and Path(cfg.steam_path).exists()
            else steam_detector.find_steam_path()
        )

        if not steam_path or not steam_path.exists():
            self.finished.emit(False, "Steam kurulum dizini bulunamadı! Lütfen Steam'in kurulu olduğundan emin olun.")
            return

        try:
            # ── Pre-check: is this game already downloaded / installed? ──
            game_already_downloaded = self._is_game_downloaded(steam_path, self.app_info.app_id, self.app_info.safe_install_dir)

            # 1. Step: Steam Shutdown if running and configured
            if cfg.auto_shutdown_steam and SteamProcessManager.is_running():
                self.progress.emit("Steam istemcisi güvenle kapatılıyor...", 15)
                logger.info("Auto-shutting down Steam for safe file writing...")
                SteamProcessManager.shutdown_steam(steam_path=steam_path, timeout_seconds=10)

            # 2. Step: Download / Transfer Manifests
            self.progress.emit("Manifest dosyaları kopyalanıyor...", 35)
            if self.package and self.package.manifests:
                from src.steam.depotcache_manager import DepotCacheManager
                dm = DepotCacheManager(steam_path)
                for mf in self.package.manifests:
                    dm.save_manifest(mf.depot_id, mf.manifest_id, mf.file_path)
            elif self.app_info.depots:
                self.progress.emit("Manifestler indiriliyor...", 45)
                manifest_downloader.download_app_manifests(
                    self.app_info,
                    steam_path,
                )

            # 3. Step: Depot Key Strategy (depends on active unlocker)
            #
            # SteamTools: Depot keys are provided at runtime via Lua setdepotkey()
            # calls. Injecting them into config.vdf is COUNTERPRODUCTIVE because
            # Steam validates these entries against Valve's servers on startup.
            # Unauthorized keys trigger a cleanup cascade that removes ACF files
            # and library registrations — causing installed games to vanish and
            # show "Buy" buttons on subsequent restarts.
            #
            # GreenLuma / other: May need config.vdf injection as a fallback
            # since they don't use Lua-based key provision.
            unlocker = get_unlocker(cfg.active_unlocker or "steamtools")
            is_steamtools = unlocker and unlocker.identifier == "steamtools"

            if is_steamtools:
                self.progress.emit("Config.vdf'den eski depot anahtarları temizleniyor...", 60)
                KeyInjector.remove_depot_keys_from_config_vdf(steam_path, self.app_info)
            else:
                self.progress.emit("Depot anahtarları konfigürasyona işleniyor...", 60)
                KeyInjector.inject_depot_keys_to_config_vdf(steam_path, self.app_info)

            # 4. Step: ACF Handling
            # If the game is already downloaded on disk, update/preserve its installed ACF.
            # If the game is NOT downloaded yet, do NOT write a fake downloading ACF (StateFlags 1026)
            # which would force Steam to queue/start downloading immediately.
            # The SteamTools Lua hook (addappid) will present the game quietly in the library.
            if game_already_downloaded:
                self.progress.emit("Mevcut kurulum korunuyor, depot bilgileri güncelleniyor...", 75)
                logger.info(
                    f"AppID {self.app_info.app_id} is already downloaded on disk. "
                    f"Merging updated depot info into existing ACF."
                )
                ACFBuilder.write_acf(
                    app_info=self.app_info,
                    library_path=self.target_library_path,
                    steam_path=steam_path,
                    state_flags=4,  # StateFullyInstalled
                    merge_if_exists=True,
                    backup_existing=True,
                )
            else:
                self.progress.emit("Kilit açıcı kütüphane kaydı hazırlanıyor...", 75)
                logger.info(
                    f"AppID {self.app_info.app_id} is not downloaded yet. "
                    f"Skipping auto-download ACF creation so the game rests quietly in the library."
                )

            # 5. Step: Inject via Active Unlocker (SteamTools / GreenLuma Hook)
            self.progress.emit("Kilit açıcı adaptörü uygulanıyor...", 85)
            if unlocker:
                unlocker.inject_game(steam_path, self.app_info, self.package)

            # 6. Step: Restart Steam and wait for full initialization
            if cfg.auto_restart_steam:
                self.progress.emit("Steam yeniden başlatılıyor...", 88)
                SteamProcessManager.start_steam(steam_path)

                self.progress.emit("Steam'in başlaması bekleniyor...", 95)
                steam_ready = SteamProcessManager.wait_until_ready(timeout_seconds=30)
                if not steam_ready:
                    logger.warning("Steam did not become fully ready in time, proceeding anyway.")

            # 7. Step: Complete without auto-install or store popups
            self.progress.emit("Tamamlandı!", 100)

            if game_already_downloaded:
                self.finished.emit(
                    True,
                    f"'{self.app_info.name}' (AppID: {self.app_info.app_id}) Steam kütüphanenizde güncellendi.\n\n"
                    f"Oyun kütüphanenizde hazır durumdadır. Dilediğiniz zaman Steam üzerinden başlatabilirsiniz."
                )
            else:
                self.finished.emit(
                    True,
                    f"'{self.app_info.name}' (AppID: {self.app_info.app_id}) Steam kütüphanenize eklendi!\n\n"
                    f"Oyun sessizce kütüphanenize yerleştirildi. İndirmek istediğiniz zaman Steam kütüphanenizden 'Yükle' butonuna basabilirsiniz."
                )

        except Exception as e:
            logger.error(f"Error during game injection pipeline: {e}")
            self.finished.emit(False, f"Aktarım hatası: {e}")

    @staticmethod
    def _is_game_downloaded(steam_path: Path, app_id: int, install_dir_name: str) -> bool:
        """Check whether the game is already downloaded by inspecting ACF state and disk contents.

        Returns True if:
        - An ACF exists with BytesDownloaded > 0, OR
        - The game's install directory under steamapps/common/ contains files
        """
        steamapps_dirs = [steam_path / "steamapps"]

        # Also check additional library folders
        for vdf_name in ["steamapps/libraryfolders.vdf", "config/libraryfolders.vdf"]:
            vdf_file = steam_path / vdf_name
            if not vdf_file.exists():
                continue
            try:
                from src.steam.vdf_parser import parse_vdf_file
                data = parse_vdf_file(vdf_file)
                lib_root = data.get("libraryfolders") or data.get("LibraryFolders") or {}
                if isinstance(lib_root, dict):
                    for _k, v in lib_root.items():
                        if isinstance(v, dict) and v.get("path"):
                            extra_dir = Path(v["path"]) / "steamapps"
                            if extra_dir not in steamapps_dirs:
                                steamapps_dirs.append(extra_dir)
            except Exception:
                pass

        for s_dir in steamapps_dirs:
            # Check ACF
            acf = s_dir / f"appmanifest_{app_id}.acf"
            if acf.exists():
                try:
                    from src.steam.vdf_parser import parse_vdf_file
                    acf_data = parse_vdf_file(acf)
                    app_state = acf_data.get("AppState", {})
                    bytes_dl = int(app_state.get("BytesDownloaded", "0") or "0")
                    if bytes_dl > 0:
                        return True
                except Exception:
                    pass

            # Check install directory on disk
            if install_dir_name:
                common_dir = s_dir / "common" / install_dir_name
                try:
                    if common_dir.exists() and any(common_dir.iterdir()):
                        return True
                except Exception:
                    pass

        return False


class HealthCheckWorker(QThread):
    """Background system diagnostic worker."""

    health_ready = pyqtSignal(object)  # SystemHealth

    def run(self) -> None:
        health = steam_detector.check_system_health()
        self.health_ready.emit(health)
