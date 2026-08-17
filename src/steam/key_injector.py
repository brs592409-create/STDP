"""Depot key validator, script injector, and Steam config.vdf merger."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from src.core.logger import get_logger
from src.core.models import AppInfo, DepotInfo
from src.steam.vdf_parser import dump_vdf_file, parse_vdf_file

logger = get_logger("steam.key_injector")

HEX_KEY_REGEX = re.compile(r"^[0-9a-fA-F]{64}$")


class KeyInjector:
    """Utilities for validating depot decryption keys, updating config.vdf, and generating Lua scripts."""

    @staticmethod
    def is_valid_hex_key(key: Optional[str]) -> bool:
        """Validate if string is a 64-character hexadecimal key."""
        if not key:
            return False
        return bool(HEX_KEY_REGEX.match(key.strip()))

    @staticmethod
    def clean_key(key: str) -> str:
        """Strip and normalize hex key string."""
        return key.strip().upper()

    @staticmethod
    def _escape_lua_string(text: str) -> str:
        """Escape double quotes and newlines for safe Lua string literals."""
        return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "").strip()

    @staticmethod
    def generate_lua_script(app_info: AppInfo) -> str:
        """Generate a complete SteamTools / OpenSteamTool / LuaTools unlocker script for an application and its depots."""
        safe_app_name = KeyInjector._escape_lua_string(app_info.name)
        lines = [
            f"-- STDP Auto-Generated Lua Script for {safe_app_name} (AppID: {app_info.app_id})",
            f'addappid({app_info.app_id}, 1, "{safe_app_name}")',
        ]

        seen_app_ids = {app_info.app_id}

        # Add all DLC / base depots
        for depot in app_info.depots:
            depot_name = depot.name or f"{app_info.name} - Depot {depot.depot_id}"
            safe_depot_name = KeyInjector._escape_lua_string(depot_name)

            if depot.depot_id not in seen_app_ids:
                lines.append(f'addappid({depot.depot_id}, 1, "{safe_depot_name}")')
                seen_app_ids.add(depot.depot_id)

            if depot.manifest_id:
                if depot.size_bytes > 0:
                    lines.append(f'setManifestid({depot.depot_id}, "{depot.manifest_id}", {depot.size_bytes})')
                else:
                    lines.append(f'setManifestid({depot.depot_id}, "{depot.manifest_id}")')

            if depot.depot_key and KeyInjector.is_valid_hex_key(depot.depot_key):
                clean_k = KeyInjector.clean_key(depot.depot_key)
                lines.append(f'setdepotkey({depot.depot_id}, "{clean_k}")')

        return "\n".join(lines) + "\n"

    @staticmethod
    def parse_lua_depot_keys(lua_content: str) -> Dict[int, str]:
        """Extract depot IDs and their corresponding hex keys from existing Lua script content."""
        keys: Dict[int, str] = {}
        # 1. Look for setdepotkey(id, "key")
        pattern1 = re.compile(r'setdepotkey\s*\(\s*(\d+)\s*,\s*["\']([0-9a-fA-F]{64})["\']\s*\)', re.IGNORECASE)
        for match in pattern1.finditer(lua_content):
            depot_id = int(match.group(1))
            key = match.group(2).upper()
            keys[depot_id] = key

        # 2. Look for addappid(id, 1, "key")
        pattern2 = re.compile(r'addappid\s*\(\s*(\d+)\s*,\s*\d+\s*,\s*["\']([0-9a-fA-F]{64})["\']\s*\)', re.IGNORECASE)
        for match in pattern2.finditer(lua_content):
            depot_id = int(match.group(1))
            key = match.group(2).upper()
            keys[depot_id] = key

        return keys

    @staticmethod
    def parse_lua_manifests(lua_content: str) -> Dict[int, Tuple[str, int]]:
        """Extract depot IDs, manifest IDs, and size from setManifestid calls."""
        manifests: Dict[int, Tuple[str, int]] = {}
        pattern = re.compile(r'setManifestid\s*\(\s*(\d+)\s*,\s*["\'](\d+)["\'](?:\s*,\s*(\d+))?\s*\)', re.IGNORECASE)
        for match in pattern.finditer(lua_content):
            depot_id = int(match.group(1))
            manifest_id = match.group(2)
            size = int(match.group(3)) if match.group(3) else 0
            manifests[depot_id] = (manifest_id, size)
        return manifests

    @staticmethod
    def parse_lua_game_name(lua_content: str) -> Optional[str]:
        """Extract clean game name from Lua comments or addappid."""
        m = re.search(r'--\s*(?:Gamename|GameName|Name)\s+(.+)', lua_content, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        m2 = re.search(r'--\s*Mainappid\s+(.+)', lua_content, re.IGNORECASE)
        if m2:
            return m2.group(1).strip()
        return None

    @staticmethod
    def inject_depot_keys_to_config_vdf(
        steam_path: Union[Path, str],
        app_info: AppInfo,
    ) -> bool:
        """Merge depot decryption keys into Steam/config/config.vdf."""
        sp = Path(steam_path)
        config_vdf = sp / "config" / "config.vdf"
        if not config_vdf.exists():
            return False

        keys_to_inject = {
            d.depot_id: KeyInjector.clean_key(d.depot_key)
            for d in app_info.depots
            if d.depot_key and KeyInjector.is_valid_hex_key(d.depot_key)
        }

        if not keys_to_inject:
            return True

        try:
            # Backup config.vdf
            bak_file = config_vdf.with_suffix(".vdf.bak")
            bak_file.write_bytes(config_vdf.read_bytes())

            data = parse_vdf_file(config_vdf)
            # Find or create Software -> Valve -> Steam -> depots
            software = data.setdefault("Software", {})
            valve = software.setdefault("Valve", {})
            steam = valve.setdefault("Steam", {})
            depots_block = steam.setdefault("depots", {})

            for depot_id, key in keys_to_inject.items():
                depots_block[str(depot_id)] = {"DecryptionKey": key}

            dump_vdf_file(config_vdf, data)
            logger.info(f"Successfully injected {len(keys_to_inject)} depot keys into {config_vdf}")
            return True
        except Exception as e:
            logger.warning(f"Could not inject depot keys into config.vdf: {e}")
            return False

    @staticmethod
    def remove_depot_keys_from_config_vdf(
        steam_path: Union[Path, str],
        app_info: AppInfo,
    ) -> bool:
        """Remove previously injected depot decryption keys from Steam/config/config.vdf.

        When Steam starts, it reads config.vdf and validates depot entries against
        Valve's servers. Any depot keys for games the user doesn't actually own are
        flagged as unauthorized. Steam then initiates a cleanup cascade that can:
        1. Remove the unauthorized depot keys from config.vdf
        2. Re-validate and remove ACF files for the affected games
        3. Deregister games from libraryfolders.vdf

        This causes previously downloaded games to disappear from the library and
        show 'Buy' buttons instead of 'Play' on subsequent Steam restarts.

        For SteamTools, depot keys are provided at runtime via Lua setdepotkey()
        calls, making config.vdf entries both unnecessary and harmful. This method
        cleans up any previously injected keys to prevent the cleanup cascade.
        """
        sp = Path(steam_path)
        config_vdf = sp / "config" / "config.vdf"
        if not config_vdf.exists():
            return True

        depot_ids_to_remove = {
            str(d.depot_id) for d in app_info.depots
            if d.depot_key and KeyInjector.is_valid_hex_key(d.depot_key)
        }

        if not depot_ids_to_remove:
            return True

        try:
            data = parse_vdf_file(config_vdf)

            # Navigate to Software -> Valve -> Steam -> depots
            depots_block = (
                data
                .get("Software", {})
                .get("Valve", {})
                .get("Steam", {})
                .get("depots", {})
            )

            if not isinstance(depots_block, dict):
                return True

            removed_count = 0
            for depot_id_str in depot_ids_to_remove:
                if depot_id_str in depots_block:
                    del depots_block[depot_id_str]
                    removed_count += 1

            if removed_count > 0:
                # Backup before writing
                bak_file = config_vdf.with_suffix(".vdf.bak")
                bak_file.write_bytes(config_vdf.read_bytes())

                dump_vdf_file(config_vdf, data)
                logger.info(
                    f"Cleaned {removed_count} previously injected depot keys from {config_vdf} "
                    f"to prevent Steam server validation cascade."
                )
            else:
                logger.debug("No previously injected depot keys found in config.vdf to clean.")

            return True
        except Exception as e:
            logger.warning(f"Could not clean depot keys from config.vdf: {e}")
            return False
