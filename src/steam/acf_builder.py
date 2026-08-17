"""Builder, updater, and libraryfolders registrar for Steam appmanifest_<appid>.acf files."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.core.logger import get_logger
from src.core.models import AppInfo, DepotInfo
from src.steam.vdf_parser import dump_vdf_file, parse_vdf_file

logger = get_logger("steam.acf_builder")


class ACFBuilder:
    """Builds appmanifest_<appid>.acf and registers apps in libraryfolders.vdf for Steam."""

    @staticmethod
    def build_acf_data(
        app_info: AppInfo,
        steam_path: Optional[Path] = None,
        ready_to_install: bool = False,
        state_flags: Optional[int] = None,
        language: str = "english",
    ) -> Dict[str, Any]:
        """Generate AppState dictionary.
        
        StateFlags is set to "1026" (StateUpdateRequired | StateReconfiguring) by default.
        BytesDownloaded is set to "0" and BytesToDownload is set to total_size.
        This makes Steam show the 'İndir' (Download) button when game files are not downloaded yet.
        """
        now_epoch = int(time.time())
        total_size = sum(d.size_bytes for d in app_info.depots)

        launcher_path = ""
        if steam_path:
            steam_exe = steam_path / "steam.exe"
            launcher_path = str(steam_exe)

        # Determine StateFlags and BytesDownloaded
        if state_flags is not None:
            final_state_flags = str(state_flags)
        else:
            final_state_flags = "1026"

        bytes_downloaded = "0"

        installed_depots: Dict[str, Dict[str, str]] = {}
        for depot in app_info.depots:
            if depot.manifest_id:
                installed_depots[str(depot.depot_id)] = {
                    "manifest": str(depot.manifest_id),
                    "size": str(depot.size_bytes),
                }

        app_state = {
            "appid": str(app_info.app_id),
            "Universe": "1",
            "LauncherPath": launcher_path,
            "name": app_info.name,
            "StateFlags": final_state_flags,
            "installdir": app_info.safe_install_dir,
            "LastUpdated": str(now_epoch),
            "UpdateResult": "0",
            "BytesToDownload": str(total_size),
            "BytesDownloaded": bytes_downloaded,
            "AutoUpdateBehavior": "0",
            "AllowOtherDownloadsWhileRunning": "0",
            "ScheduledAutoUpdate": "0",
            "InstalledDepots": installed_depots,
            "UserConfig": {
                "language": language,
            },
        }

        return {"AppState": app_state}

    @staticmethod
    def merge_with_existing(
        existing_vdf: Dict[str, Any],
        app_info: AppInfo,
        ready_to_install: bool = False,
        state_flags: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Merge newly added depots into existing ACF without destroying user settings."""
        app_state = existing_vdf.get("AppState", {})
        if not app_state:
            return ACFBuilder.build_acf_data(
                app_info, ready_to_install=ready_to_install, state_flags=state_flags
            )

        # Update core fields if missing
        if "name" not in app_state or not app_state["name"]:
            app_state["name"] = app_info.name
        if "installdir" not in app_state or not app_state["installdir"]:
            app_state["installdir"] = app_info.safe_install_dir

        app_state["LastUpdated"] = str(int(time.time()))

        if state_flags is not None:
            app_state["StateFlags"] = str(state_flags)
        else:
            app_state["StateFlags"] = "1026"

        # Merge installed depots
        installed_depots = app_state.get("InstalledDepots", {})
        if not isinstance(installed_depots, dict):
            installed_depots = {}

        for depot in app_info.depots:
            if depot.manifest_id:
                depot_str = str(depot.depot_id)
                installed_depots[depot_str] = {
                    "manifest": str(depot.manifest_id),
                    "size": str(depot.size_bytes),
                }

        app_state["InstalledDepots"] = installed_depots

        # Recalculate total download size
        total_size = sum(
            int(d.get("size", 0)) for d in installed_depots.values() if isinstance(d, dict)
        )
        app_state["BytesToDownload"] = str(total_size)

        # Preserve existing BytesDownloaded if game was already downloaded.
        # Resetting this to "0" would make Steam think the game needs to be
        # re-downloaded, causing installed games to lose their "Play" state.
        existing_bytes_dl = int(app_state.get("BytesDownloaded", "0") or "0")
        if existing_bytes_dl <= 0:
            app_state["BytesDownloaded"] = "0"
        # else: keep the existing BytesDownloaded value untouched

        return {"AppState": app_state}

    @staticmethod
    def register_in_libraryfolders(
        steam_path: Union[Path, str],
        library_path: Union[Path, str],
        app_id: int,
        total_size: int = 0,
    ) -> bool:
        """Ensure AppID is registered under the matching library folder in libraryfolders.vdf."""
        sp = Path(steam_path)
        lp = Path(library_path)

        vdf_candidates = [
            sp / "steamapps" / "libraryfolders.vdf",
            sp / "config" / "libraryfolders.vdf",
        ]

        vdf_file = next((c for c in vdf_candidates if c.exists()), sp / "steamapps" / "libraryfolders.vdf")
        if not vdf_file.exists():
            return False

        try:
            # Backup libraryfolders.vdf
            bak_file = vdf_file.with_suffix(".vdf.bak")
            bak_file.write_bytes(vdf_file.read_bytes())

            data = parse_vdf_file(vdf_file)
            lib_root = data.get("libraryfolders") or data.get("LibraryFolders")
            if not isinstance(lib_root, dict):
                return False

            updated = False
            target_folder_key = None
            first_folder_key = None

            for folder_key, folder_val in lib_root.items():
                if isinstance(folder_val, dict):
                    if first_folder_key is None:
                        first_folder_key = folder_key
                    f_path_str = folder_val.get("path")
                    if f_path_str:
                        try:
                            if Path(f_path_str).resolve() == lp.resolve():
                                target_folder_key = folder_key
                                break
                        except Exception:
                            if str(f_path_str).lower() == str(lp).lower():
                                target_folder_key = folder_key
                                break

            # Fallback to the first library folder (folder 0) if matching path wasn't found
            key_to_use = target_folder_key if target_folder_key is not None else first_folder_key
            if key_to_use is not None and isinstance(lib_root.get(key_to_use), dict):
                apps_dict = lib_root[key_to_use].setdefault("apps", {})
                if isinstance(apps_dict, dict):
                    apps_dict[str(app_id)] = str(total_size)
                    updated = True

            if updated:
                dump_vdf_file(vdf_file, data)
                logger.info(f"Registered AppID {app_id} in {vdf_file} under folder {key_to_use}")
                return True
        except Exception as e:
            logger.warning(f"Could not update libraryfolders.vdf: {e}")

        return False

    @staticmethod
    def write_acf(
        app_info: AppInfo,
        library_path: Union[Path, str],
        steam_path: Optional[Path] = None,
        ready_to_install: bool = False,
        state_flags: Optional[int] = None,
        merge_if_exists: bool = True,
        backup_existing: bool = True,
    ) -> Path:
        """Write or merge appmanifest_<appid>.acf and register with libraryfolders."""
        lib = Path(library_path)
        steamapps_dir = lib / "steamapps" if (lib / "steamapps").exists() or lib.name != "steamapps" else lib
        steamapps_dir.mkdir(parents=True, exist_ok=True)

        acf_file = steamapps_dir / f"appmanifest_{app_info.app_id}.acf"

        if acf_file.exists() and merge_if_exists:
            try:
                if backup_existing:
                    backup_path = steamapps_dir / f"appmanifest_{app_info.app_id}.acf.bak"
                    backup_path.write_bytes(acf_file.read_bytes())
                    logger.debug(f"Backed up existing ACF to {backup_path}")

                existing_data = parse_vdf_file(acf_file)
                final_data = ACFBuilder.merge_with_existing(
                    existing_data, app_info, ready_to_install=ready_to_install, state_flags=state_flags
                )
            except Exception as e:
                logger.warning(f"Failed to merge existing ACF, generating fresh: {e}")
                final_data = ACFBuilder.build_acf_data(
                    app_info, steam_path, ready_to_install=ready_to_install, state_flags=state_flags
                )
        else:
            final_data = ACFBuilder.build_acf_data(
                app_info, steam_path, ready_to_install=ready_to_install, state_flags=state_flags
            )

        dump_vdf_file(acf_file, final_data)
        logger.info(f"Successfully wrote ACF manifest (StateFlags: {final_data.get('AppState', {}).get('StateFlags')}) to {acf_file}")

        # Register in libraryfolders.vdf
        if steam_path:
            ACFBuilder.register_in_libraryfolders(
                steam_path=steam_path,
                library_path=lib,
                app_id=app_info.app_id,
                total_size=app_info.total_size_bytes,
            )

        return acf_file

    @staticmethod
    def remove_app_manifest_and_registration(
        steam_path: Union[Path, str],
        app_id: int,
    ) -> None:
        """Remove any fake ACF files and libraryfolders entries so Steam displays the clean 'YÜKLE' (Install) button.

        IMPORTANT: This method now checks whether the game has already been
        downloaded before removing the ACF. If it detects that the game files
        are present on disk, the ACF and library registration are preserved to
        avoid breaking an existing installation.
        """
        sp = Path(steam_path)
        candidate_dirs = [sp / "steamapps"]

        # Check all possible libraryfolders.vdf locations for additional library paths
        vdf_candidates = [
            sp / "steamapps" / "libraryfolders.vdf",
            sp / "config" / "libraryfolders.vdf",
        ]
        for vdf_file in vdf_candidates:
            if not vdf_file.exists():
                continue
            try:
                data = parse_vdf_file(vdf_file)
                lib_root = data.get("libraryfolders") or data.get("LibraryFolders") or {}
                if isinstance(lib_root, dict):
                    updated = False
                    for folder_key, folder_val in lib_root.items():
                        if isinstance(folder_val, dict):
                            f_path = folder_val.get("path")
                            if f_path:
                                candidate_dirs.append(Path(f_path) / "steamapps")
                            apps_dict = folder_val.get("apps")
                            if isinstance(apps_dict, dict) and str(app_id) in apps_dict:
                                del apps_dict[str(app_id)]
                                updated = True
                    if updated:
                        dump_vdf_file(vdf_file, data)
                        logger.info(f"Cleaned AppID {app_id} from {vdf_file}")
            except Exception as e:
                logger.warning(f"Error cleaning libraryfolders for AppID {app_id}: {e}")

        # Deduplicate candidate directories
        unique_dirs = []
        for d in candidate_dirs:
            if d not in unique_dirs:
                unique_dirs.append(d)

        for s_dir in unique_dirs:
            acf = s_dir / f"appmanifest_{app_id}.acf"
            if acf.exists():
                # ── Guard: do NOT delete ACF for games already downloaded ──
                try:
                    acf_data = parse_vdf_file(acf)
                    app_state = acf_data.get("AppState", {})
                    bytes_downloaded = int(app_state.get("BytesDownloaded", "0") or "0")
                    install_dir_name = app_state.get("installdir", "")

                    # Check if game files actually exist on disk
                    game_installed_on_disk = False
                    if install_dir_name:
                        common_dir = s_dir / "common" / install_dir_name
                        if common_dir.exists() and any(common_dir.iterdir()):
                            game_installed_on_disk = True

                    if bytes_downloaded > 0 or game_installed_on_disk:
                        logger.info(
                            f"Skipping ACF removal for AppID {app_id}: game is already downloaded "
                            f"(BytesDownloaded={bytes_downloaded}, files_on_disk={game_installed_on_disk}). "
                            f"Preserving existing installation record."
                        )
                        continue
                except Exception as parse_err:
                    logger.debug(f"Could not parse ACF to check download state, proceeding with removal: {parse_err}")

                try:
                    acf.unlink()
                    logger.info(f"Removed uninstalled ACF: {acf}")
                except Exception as e:
                    logger.warning(f"Failed to remove ACF {acf}: {e}")
