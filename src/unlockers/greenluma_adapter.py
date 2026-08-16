"""GreenLuma AppList hook adapter with collision-free merge and backup."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from src.core.logger import get_logger
from src.core.models import AppInfo, GamePackage
from src.unlockers.base import UnlockerAdapter

logger = get_logger("unlockers.greenluma")


class GreenLumaAdapter(UnlockerAdapter):
    """Adapter for GreenLuma using sequential AppList text files (0.txt, 1.txt, ...)."""

    @property
    def name(self) -> str:
        return "GreenLuma (AppList)"

    @property
    def identifier(self) -> str:
        return "greenluma"

    @property
    def description(self) -> str:
        return "GreenLuma AppList adaptörü. Steam/AppList/ altında sıralı 0.txt, 1.txt dosyaları ile çalışır."

    def _get_applist_dir(self, steam_path: Union[Path, str]) -> Path:
        """Resolve Steam/AppList directory."""
        sp = Path(steam_path)
        return sp / "AppList"

    def is_installed(self, steam_path: Union[Path, str]) -> bool:
        """Check if AppList directory exists."""
        applist_dir = self._get_applist_dir(steam_path)
        return applist_dir.exists()

    def install_hook(self, steam_path: Union[Path, str]) -> bool:
        """Ensure AppList directory exists."""
        try:
            applist_dir = self._get_applist_dir(steam_path)
            applist_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initialized GreenLuma AppList folder at: {applist_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize AppList folder: {e}")
            return False

    def backup_applist(self, steam_path: Union[Path, str]) -> Optional[Path]:
        """Create a backup of the current AppList directory."""
        applist_dir = self._get_applist_dir(steam_path)
        if not applist_dir.exists() or not any(applist_dir.iterdir()):
            return None

        backup_dir = applist_dir.parent / "AppList_backup"
        try:
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            shutil.copytree(applist_dir, backup_dir)
            logger.info(f"GreenLuma AppList backed up to {backup_dir}")
            return backup_dir
        except Exception as e:
            logger.warning(f"Could not backup AppList directory: {e}")
            return None

    def _scan_applist_entries(self, applist_dir: Path) -> Tuple[Dict[int, int], int]:
        """Scan all indexed files like '0.txt', '1.txt'. Returns (index_to_appid_map, max_index)."""
        entries: Dict[int, int] = {}
        max_idx = -1

        if not applist_dir.exists():
            return entries, max_idx

        for item in applist_dir.glob("*.txt"):
            if item.stem.isdigit():
                idx = int(item.stem)
                max_idx = max(max_idx, idx)
                try:
                    content = item.read_text(encoding="utf-8").strip()
                    if content.isdigit():
                        entries[idx] = int(content)
                except Exception as e:
                    logger.warning(f"Could not read {item}: {e}")

        return entries, max_idx

    def inject_game(
        self,
        steam_path: Union[Path, str],
        app_info: AppInfo,
        package: Optional[GamePackage] = None,
    ) -> bool:
        """Add AppID and all associated DepotIDs to AppList sequentially without overwriting."""
        try:
            self.install_hook(steam_path)
            applist_dir = self._get_applist_dir(steam_path)

            # Create safety backup
            self.backup_applist(steam_path)

            entries, max_idx = self._scan_applist_entries(applist_dir)
            existing_ids: Set[int] = set(entries.values())

            # Collect IDs to add
            ids_to_add: List[int] = []
            if app_info.app_id not in existing_ids:
                ids_to_add.append(app_info.app_id)

            for depot in app_info.depots:
                if depot.depot_id not in existing_ids and depot.depot_id not in ids_to_add:
                    ids_to_add.append(depot.depot_id)

            if not ids_to_add:
                logger.info(f"All IDs for {app_info.name} (AppID: {app_info.app_id}) are already in AppList.")
                return True

            current_idx = max_idx + 1
            for target_id in ids_to_add:
                file_path = applist_dir / f"{current_idx}.txt"
                file_path.write_text(f"{target_id}\n", encoding="utf-8")
                logger.debug(f"Wrote GreenLuma entry: {file_path.name} -> {target_id}")
                current_idx += 1

            logger.info(
                f"Successfully injected {len(ids_to_add)} IDs into GreenLuma AppList for {app_info.name}."
            )
            return True
        except Exception as e:
            logger.error(f"Failed to inject game into GreenLuma AppList: {e}")
            return False

    def remove_game(self, steam_path: Union[Path, str], app_id: int) -> bool:
        """Remove AppID and re-index the remaining AppList entries gaplessly (0..N)."""
        try:
            applist_dir = self._get_applist_dir(steam_path)
            if not applist_dir.exists():
                return True

            self.backup_applist(steam_path)
            entries, _ = self._scan_applist_entries(applist_dir)

            # Filter out entries matching app_id
            remaining_ids = [val for idx, val in sorted(entries.items()) if val != app_id]

            if len(remaining_ids) == len(entries):
                logger.info(f"AppID {app_id} was not found in GreenLuma AppList.")
                return True

            # Clear current txt files and re-index cleanly
            for item in applist_dir.glob("*.txt"):
                if item.stem.isdigit():
                    item.unlink()

            for new_idx, rem_id in enumerate(remaining_ids):
                (applist_dir / f"{new_idx}.txt").write_text(f"{rem_id}\n", encoding="utf-8")

            logger.info(f"Removed AppID {app_id} and re-indexed {len(remaining_ids)} GreenLuma entries.")
            return True
        except Exception as e:
            logger.error(f"Failed to remove AppID {app_id} from GreenLuma: {e}")
            return False

    def list_injected_games(self, steam_path: Union[Path, str]) -> List[int]:
        """List all unique IDs registered in the AppList directory."""
        applist_dir = self._get_applist_dir(steam_path)
        entries, _ = self._scan_applist_entries(applist_dir)
        return sorted(list(set(entries.values())))

    def uninstall_hook(self, steam_path: Union[Path, str]) -> bool:
        """Backup and remove AppList folder."""
        try:
            applist_dir = self._get_applist_dir(steam_path)
            if applist_dir.exists():
                self.backup_applist(steam_path)
                shutil.rmtree(applist_dir)
                logger.info("GreenLuma AppList directory removed.")
            return True
        except Exception as e:
            logger.error(f"Failed to uninstall GreenLuma hook: {e}")
            return False
