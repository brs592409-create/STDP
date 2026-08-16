"""Depot key validator, script injector, and Steam config.vdf merger."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

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
        return KeyInjector.merge_or_generate_lua_script(app_info, custom_lua_content=None)

    @staticmethod
    def merge_or_generate_lua_script(
        app_info: AppInfo,
        custom_lua_content: Optional[str] = None,
    ) -> str:
        """Merge custom Lua script with complete depot manifest IDs, depot keys, and addappids."""
        safe_app_name = KeyInjector._escape_lua_string(app_info.name)

        existing_lines: List[str] = []
        parsed_keys: Dict[int, str] = {}
        parsed_manifests: Dict[int, Tuple[str, int]] = {}
        parsed_appids: set[int] = set()

        if custom_lua_content:
            parsed_keys = KeyInjector.parse_lua_depot_keys(custom_lua_content)
            parsed_manifests = KeyInjector.parse_lua_manifests(custom_lua_content)
            for m in re.finditer(r'addappid\s*\(\s*(\d+)', custom_lua_content, re.IGNORECASE):
                parsed_appids.add(int(m.group(1)))

            # Keep non-header custom lines
            for line in custom_lua_content.strip().splitlines():
                line_str = line.strip()
                if line_str and not line_str.startswith(("-- STDP Auto-Generated", "-- STDP Complete")):
                    existing_lines.append(line_str)

        lines: List[str] = [
            f"-- STDP Complete Lua Script for {safe_app_name} (AppID: {app_info.app_id})",
        ]

        # 1. Main Game addappid (if not already present in existing lines)
        main_app_added = False
        for l in existing_lines:
            if re.search(rf'addappid\s*\(\s*{app_info.app_id}\b', l, re.IGNORECASE):
                main_app_added = True
                break
        if not main_app_added:
            lines.append(f'addappid({app_info.app_id}, 1, "{safe_app_name}")')

        # 2. Add existing custom lines
        for l in existing_lines:
            lines.append(l)

        # 3. Ensure ALL depots from app_info are added with addappid, setManifestid, and setdepotkey
        seen_depot_ids = set(parsed_appids)
        seen_depot_ids.add(app_info.app_id)

        for depot in app_info.depots:
            depot_name = depot.name or f"{app_info.name} - Depot {depot.depot_id}"
            safe_depot_name = KeyInjector._escape_lua_string(depot_name)

            # Ensure addappid for depot
            if depot.depot_id not in seen_depot_ids:
                lines.append(f'addappid({depot.depot_id}, 1, "{safe_depot_name}")')
                seen_depot_ids.add(depot.depot_id)

            # Ensure setManifestid for depot if manifest_id is present
            if depot.manifest_id:
                cur_man = parsed_manifests.get(depot.depot_id)
                # If not present or manifest ID differs, append correct setManifestid
                if not cur_man or cur_man[0] != str(depot.manifest_id):
                    if depot.size_bytes > 0:
                        lines.append(f'setManifestid({depot.depot_id}, "{depot.manifest_id}", {depot.size_bytes})')
                    else:
                        lines.append(f'setManifestid({depot.depot_id}, "{depot.manifest_id}")')

            # Ensure setdepotkey for depot if key is present
            if depot.depot_key and KeyInjector.is_valid_hex_key(depot.depot_key):
                clean_k = KeyInjector.clean_key(depot.depot_key)
                if parsed_keys.get(depot.depot_id) != clean_k:
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
        """Merge depot decryption keys into Steam/config/config.vdf across all standard VDF hierarchy levels."""
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

            # 1. Primary modern Steam path: InstallConfigStore -> Software -> Valve -> Steam -> depots
            ics = data.setdefault("InstallConfigStore", {})
            if isinstance(ics, dict):
                ics_sw = ics.setdefault("Software", {})
                if isinstance(ics_sw, dict):
                    ics_vl = ics_sw.setdefault("Valve", {})
                    if isinstance(ics_vl, dict):
                        ics_st = ics_vl.setdefault("Steam", {})
                        if isinstance(ics_st, dict):
                            ics_depots = ics_st.setdefault("depots", {})
                            if isinstance(ics_depots, dict):
                                for depot_id, key in keys_to_inject.items():
                                    ics_depots[str(depot_id)] = {"DecryptionKey": key}

            # 2. Secondary flat path: Software -> Valve -> Steam -> depots
            sw = data.setdefault("Software", {})
            if isinstance(sw, dict):
                vl = sw.setdefault("Valve", {})
                if isinstance(vl, dict):
                    st = vl.setdefault("Steam", {})
                    if isinstance(st, dict):
                        depots_block = st.setdefault("depots", {})
                        if isinstance(depots_block, dict):
                            for depot_id, key in keys_to_inject.items():
                                depots_block[str(depot_id)] = {"DecryptionKey": key}

            # 3. Direct root depots (for custom unpackers)
            root_depots = data.setdefault("depots", {})
            if isinstance(root_depots, dict):
                for depot_id, key in keys_to_inject.items():
                    root_depots[str(depot_id)] = {"DecryptionKey": key}

            dump_vdf_file(config_vdf, data)
            logger.info(f"Successfully injected {len(keys_to_inject)} depot keys into {config_vdf} (InstallConfigStore + Software)")
            return True
        except Exception as e:
            logger.warning(f"Could not inject depot keys into config.vdf: {e}")
            return False
