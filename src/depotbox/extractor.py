"""Archive and file package extractor for manual drag-and-drop ingestion."""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from src.core.logger import get_logger
from src.core.models import AppInfo, DepotInfo, GamePackage, ManifestFile
from src.steam.depotcache_manager import DepotCacheManager
from src.steam.key_injector import KeyInjector

logger = get_logger("depotbox.extractor")


class ArchiveExtractor:
    """Extracts and parses .zip, .manifest, .lua, and .vdf packages for Steam injection."""

    def __init__(self, extract_root: Optional[Path] = None) -> None:
        self.extract_root = extract_root or Path(tempfile.gettempdir()) / "STDP_Extracted"
        self.extract_root.mkdir(parents=True, exist_ok=True)

    def extract_package(self, source_path: Union[Path, str]) -> GamePackage:
        """Process an archive or single file, returning a structured GamePackage."""
        path = Path(source_path)
        if not path.exists():
            raise FileNotFoundError(f"Source package not found: {path}")

        logger.info(f"Extracting package: {path.name}")

        # If it is a ZIP archive
        if path.suffix.lower() == ".zip":
            return self._extract_zip(path)

        # If it is a RAR or 7z archive
        elif path.suffix.lower() in [".rar", ".7z", ".tar", ".gz"]:
            return self._extract_generic_archive(path)

        # If it is a raw .manifest file
        elif path.suffix.lower() == ".manifest":
            return self._process_single_manifest(path)

        # If it is a raw .lua file
        elif path.suffix.lower() == ".lua":
            return self._process_single_lua(path)

        # Fallback / Directory
        elif path.is_dir():
            return self._process_extracted_directory(path, source_archive=path)

        else:
            raise ValueError(f"Unsupported package format: {path.suffix}")

    def _extract_zip(self, zip_path: Path) -> GamePackage:
        """Unpack ZIP archive and analyze its contents."""
        target_dir = self.extract_root / f"{zip_path.stem}_{int(os.path.getmtime(zip_path))}"
        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)

        return self._process_extracted_directory(target_dir, source_archive=zip_path)

    def _extract_generic_archive(self, archive_path: Path) -> GamePackage:
        """Unpack .rar, .7z or other archives using bundled 7-Zip binaries."""
        import shutil
        import subprocess

        target_dir = self.extract_root / f"{archive_path.stem}_{int(os.path.getmtime(archive_path))}"
        target_dir.mkdir(parents=True, exist_ok=True)

        project_root = Path(__file__).resolve().parent.parent.parent
        seven_zip_candidates = [
            project_root / "bundled_installers" / "7z.exe",
            project_root / "bundled_installers" / "7za.exe",
            Path(r"C:\Program Files\7-Zip\7z.exe"),
            Path(r"C:\Program Files (x86)\7-Zip\7z.exe"),
        ]
        seven_zip = next((p for p in seven_zip_candidates if p.exists()), None)
        if seven_zip:
            subprocess.run([str(seven_zip), "x", str(archive_path), f"-o{str(target_dir)}", "-y"], check=True)
            return self._process_extracted_directory(target_dir, source_archive=archive_path)

        raise RuntimeError(f"Cannot extract {archive_path.suffix}: 7-Zip extractor not found in bundled_installers.")

    def _process_extracted_directory(
        self, directory: Path, source_archive: Optional[Path] = None
    ) -> GamePackage:
        """Scan directory recursively for manifests, lua scripts, and metadata."""
        manifest_files: List[ManifestFile] = []
        lua_scripts: Dict[str, str] = {}
        depot_keys: Dict[int, str] = {}
        detected_app_id: Optional[int] = None
        game_name: str = source_archive.stem if source_archive else directory.name

        # 1. Find all .manifest files
        for f in directory.rglob("*.manifest"):
            parsed = DepotCacheManager.parse_filename(f.name)
            if parsed:
                depot_id, manifest_id = parsed
                try:
                    size = f.stat().st_size
                except OSError:
                    size = 0
                manifest_files.append(
                    ManifestFile(
                        file_path=f,
                        depot_id=depot_id,
                        manifest_id=manifest_id,
                        size_bytes=size,
                    )
                )

        # 2. Find all .lua files
        parsed_manifests: Dict[int, Tuple[str, int]] = {}
        for f in directory.rglob("*.lua"):
            try:
                content = f.read_text(encoding="utf-8")
                lua_scripts[f.name] = content

                # Extract depot keys from Lua script
                parsed_keys = KeyInjector.parse_lua_depot_keys(content)
                depot_keys.update(parsed_keys)

                # Extract setManifestid calls
                parsed_mans = KeyInjector.parse_lua_manifests(content)
                parsed_manifests.update(parsed_mans)

                # Extract clean game name from comment or non-key addappid
                parsed_name = KeyInjector.parse_lua_game_name(content)
                if parsed_name:
                    game_name = parsed_name

                # Look for main AppID
                stem_id = int(f.stem) if f.stem.isdigit() else None
                if stem_id and detected_app_id is None:
                    detected_app_id = stem_id

                match = re.search(r'addappid\s*\(\s*(\d+)\s*,\s*1\s*,\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                if match:
                    app_num = int(match.group(1))
                    val = match.group(2)
                    if not KeyInjector.is_valid_hex_key(val) and not parsed_name:
                        game_name = val
                    if detected_app_id is None:
                        detected_app_id = app_num
            except Exception as e:
                logger.warning(f"Error reading Lua file {f}: {e}")

        # Fallback detection for AppID
        if detected_app_id is None:
            # Check if source archive stem starts with digits (e.g. "1091500_Cyberpunk.zip")
            stem_match = re.match(r"^(\d+)", source_archive.stem if source_archive else directory.name)
            if stem_match:
                detected_app_id = int(stem_match.group(1))
            elif manifest_files:
                # Approximate from first depot ID
                detected_app_id = manifest_files[0].depot_id

        if detected_app_id is None:
            detected_app_id = 0

        # Construct DepotInfo list from manifest files AND Lua definitions
        depots_map: Dict[int, DepotInfo] = {}

        # 1. From local manifest files
        for mf in manifest_files:
            key = depot_keys.get(mf.depot_id)
            depots_map[mf.depot_id] = DepotInfo(
                depot_id=mf.depot_id,
                manifest_id=mf.manifest_id,
                depot_key=key,
                size_bytes=mf.size_bytes,
            )

        # 2. From Lua setManifestid
        for did, (mid, size) in parsed_manifests.items():
            key = depot_keys.get(did)
            if did in depots_map:
                if not depots_map[did].manifest_id:
                    depots_map[did].manifest_id = mid
                if size > 0:
                    depots_map[did].size_bytes = size
                if key and not depots_map[did].depot_key:
                    depots_map[did].depot_key = key
            else:
                depots_map[did] = DepotInfo(
                    depot_id=did,
                    manifest_id=mid,
                    depot_key=key,
                    size_bytes=size,
                )

        # 3. From remaining depot keys
        for did, key in depot_keys.items():
            if did != detected_app_id and did not in depots_map:
                depots_map[did] = DepotInfo(
                    depot_id=did,
                    depot_key=key,
                )

        depots = list(depots_map.values())

        app_info = AppInfo(
            app_id=detected_app_id,
            name=game_name,
            depots=depots,
            header_url=f"https://cdn.cloudflare.steamstatic.com/steam/apps/{detected_app_id}/header.jpg",
        )

        return GamePackage(
            app_info=app_info,
            manifests=manifest_files,
            lua_scripts=lua_scripts,
            source_archive=source_archive,
            status="ready",
        )

    def _process_single_manifest(self, manifest_path: Path) -> GamePackage:
        """Convert a single .manifest file into a minimal GamePackage."""
        parsed = DepotCacheManager.parse_filename(manifest_path.name)
        if not parsed:
            raise ValueError(f"Filename does not match <depotid>_<manifestid>.manifest: {manifest_path.name}")

        depot_id, manifest_id = parsed
        size = manifest_path.stat().st_size
        mf = ManifestFile(
            file_path=manifest_path,
            depot_id=depot_id,
            manifest_id=manifest_id,
            size_bytes=size,
        )

        depot = DepotInfo(depot_id=depot_id, manifest_id=manifest_id, size_bytes=size)
        app = AppInfo(app_id=depot_id, name=f"Depot {depot_id}", depots=[depot])

        return GamePackage(
            app_info=app,
            manifests=[mf],
            source_archive=manifest_path,
            status="ready",
        )

    def _process_single_lua(self, lua_path: Path) -> GamePackage:
        """Convert a single .lua script file into a GamePackage."""
        content = lua_path.read_text(encoding="utf-8")
        depot_keys = KeyInjector.parse_lua_depot_keys(content)

        app_id = int(lua_path.stem) if lua_path.stem.isdigit() else 0
        game_name = lua_path.stem

        match = re.search(r'addappid\s*\(\s*(\d+)\s*,\s*1\s*,\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
        if match:
            app_id = int(match.group(1))
            game_name = match.group(2)

        depots: List[DepotInfo] = []
        for did, key in depot_keys.items():
            depots.append(DepotInfo(depot_id=did, depot_key=key))

        app = AppInfo(app_id=app_id, name=game_name, depots=depots)
        return GamePackage(
            app_info=app,
            lua_scripts={lua_path.name: content},
            source_archive=lua_path,
            status="ready",
        )


# Global singleton instance
archive_extractor = ArchiveExtractor()
