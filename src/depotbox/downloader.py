"""Asynchronous and chunked manifest file downloader."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, List, Optional, Union
import requests

from src.core.logger import get_logger
from src.core.models import AppInfo, DepotInfo, ManifestFile
from src.steam.depotcache_manager import DepotCacheManager

logger = get_logger("depotbox.downloader")

# Callback signatures for UI progress updates
# ProgressCallback = (bytes_downloaded, total_bytes)
ProgressCallback = Callable[[int, int], None]
# BatchProgressCallback = (current_filename, current_bytes, total_bytes)
BatchProgressCallback = Callable[[str, int, int], None]


class ManifestDownloader:
    """Handles downloading and validating Steam manifest binary files."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout_seconds: int = 20,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout_seconds

    def download_manifest(
        self,
        url: str,
        target_path: Union[Path, str],
        expected_sha256: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> bool:
        """Stream download a manifest file to disk with hash validation and atomic write."""
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_target = target.with_suffix(".tmp")

        try:
            with self.session.get(url, stream=True, timeout=self.timeout) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("Content-Length", 0))

                sha256 = hashlib.sha256()
                downloaded_bytes = 0

                with open(temp_target, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            sha256.update(chunk)
                            downloaded_bytes += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded_bytes, total_bytes)

                # Check hash if provided
                if expected_sha256:
                    actual_sha = sha256.hexdigest().lower()
                    if actual_sha != expected_sha256.strip().lower():
                        logger.error(
                            f"Checksum mismatch for {target.name}: expected {expected_sha256}, got {actual_sha}"
                        )
                        if temp_target.exists():
                            temp_target.unlink()
                        return False

                # Atomic rename
                if target.exists():
                    target.unlink()
                temp_target.rename(target)
                logger.info(f"Successfully downloaded manifest: {target.name} ({downloaded_bytes} bytes)")
                return True

        except Exception as e:
            logger.error(f"Failed to download manifest from {url}: {e}")
            if temp_target.exists():
                temp_target.unlink()
            return False

    def download_app_manifests(
        self,
        app_info: AppInfo,
        steam_path: Union[Path, str],
        batch_callback: Optional[BatchProgressCallback] = None,
    ) -> List[ManifestFile]:
        """Download all manifests specified in an AppInfo directly into Steam/depotcache."""
        depot_mgr = DepotCacheManager(steam_path)
        depot_mgr.ensure_dir()

        downloaded_manifests: List[ManifestFile] = []

        for depot in app_info.depots:
            if not depot.manifest_id or not depot.manifest_url:
                continue

            target_path = depot_mgr.get_manifest_path(depot.depot_id, depot.manifest_id)

            def _on_progress(current: int, total: int) -> None:
                if batch_callback:
                    batch_callback(target_path.name, current, total)

            success = self.download_manifest(
                url=depot.manifest_url,
                target_path=target_path,
                progress_callback=_on_progress,
            )

            if success and target_path.exists():
                downloaded_manifests.append(
                    ManifestFile(
                        file_path=target_path,
                        depot_id=depot.depot_id,
                        manifest_id=depot.manifest_id,
                        size_bytes=target_path.stat().st_size,
                    )
                )

        return downloaded_manifests


# Global singleton instance
manifest_downloader = ManifestDownloader()
