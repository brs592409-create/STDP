"""Manager for Steam depotcache manifest storage and validation."""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Union

from src.core.logger import get_logger
from src.core.models import ManifestFile

logger = get_logger("steam.depotcache_manager")

MANIFEST_NAME_REGEX = re.compile(r"^(\d+)_(\d+)\.manifest$", re.IGNORECASE)


class DepotCacheManager:
    """Handles manifest placement, verification, and inspection in Steam/depotcache."""

    def __init__(self, steam_path: Union[Path, str]) -> None:
        self.steam_path = Path(steam_path)
        self.depotcache_dir = self.steam_path / "depotcache"

    def ensure_dir(self) -> Path:
        """Ensure depotcache directory exists and is writable."""
        self.depotcache_dir.mkdir(parents=True, exist_ok=True)
        return self.depotcache_dir

    @staticmethod
    def parse_filename(filename: str) -> Optional[Tuple[int, str]]:
        """Extract (depot_id, manifest_id) from standard filename like '1091501_8472918392817281920.manifest'."""
        match = MANIFEST_NAME_REGEX.match(filename)
        if match:
            return int(match.group(1)), match.group(2)
        return None

    def get_manifest_path(self, depot_id: int, manifest_id: str) -> Path:
        """Get expected path for a specific manifest file."""
        return self.depotcache_dir / f"{depot_id}_{manifest_id}.manifest"

    def has_manifest(self, depot_id: int, manifest_id: str) -> bool:
        """Check if a manifest file already exists in depotcache and is non-empty."""
        path = self.get_manifest_path(depot_id, manifest_id)
        return path.exists() and path.stat().st_size > 0

    @staticmethod
    def calculate_sha256(file_path: Path) -> str:
        """Calculate SHA256 hexadecimal digest of a file in chunks."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def save_manifest(
        self,
        depot_id: int,
        manifest_id: str,
        source: Union[bytes, Path, str],
        overwrite: bool = True,
    ) -> Path:
        """Save bytes or copy a manifest file to Steam/depotcache and Steam/config/depotcache."""
        self.ensure_dir()
        target_path = self.get_manifest_path(depot_id, manifest_id)

        # Also ensure fallback directory in config/depotcache
        config_depotcache = self.steam_path / "config" / "depotcache"
        config_depotcache.mkdir(parents=True, exist_ok=True)
        config_target = config_depotcache / f"{depot_id}_{manifest_id}.manifest"

        if target_path.exists() and not overwrite:
            logger.debug(f"Manifest already exists and overwrite is disabled: {target_path}")
            return target_path

        if isinstance(source, bytes):
            target_path.write_bytes(source)
            try:
                config_target.write_bytes(source)
            except Exception:
                pass
        else:
            src_path = Path(source)
            if not src_path.exists():
                raise FileNotFoundError(f"Source manifest file not found: {src_path}")
            shutil.copy2(src_path, target_path)
            try:
                shutil.copy2(src_path, config_target)
            except Exception:
                pass

        logger.info(f"Saved manifest to {target_path} (size: {target_path.stat().st_size} bytes)")
        return target_path

    def verify_manifest(
        self,
        depot_id: int,
        manifest_id: str,
        expected_sha256: Optional[str] = None,
    ) -> bool:
        """Verify existence and optional SHA256 checksum of a manifest in depotcache."""
        target_path = self.get_manifest_path(depot_id, manifest_id)
        if not target_path.exists() or target_path.stat().st_size == 0:
            return False

        if expected_sha256:
            actual_sha = self.calculate_sha256(target_path)
            return actual_sha.lower() == expected_sha256.strip().lower()

        return True

    def list_installed_manifests(self) -> List[ManifestFile]:
        """List all valid manifest files present in the depotcache directory."""
        if not self.depotcache_dir.exists():
            return []

        manifests: List[ManifestFile] = []
        for file in self.depotcache_dir.glob("*.manifest"):
            parsed = self.parse_filename(file.name)
            if parsed:
                depot_id, manifest_id = parsed
                try:
                    size = file.stat().st_size
                except OSError:
                    size = 0
                manifests.append(
                    ManifestFile(
                        file_path=file,
                        depot_id=depot_id,
                        manifest_id=manifest_id,
                        size_bytes=size,
                    )
                )

        return manifests
