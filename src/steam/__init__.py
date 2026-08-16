"""Steam integration layer package exports."""

from src.steam.vdf_parser import (
    dump_vdf_file,
    dump_vdf_text,
    parse_vdf_file,
    parse_vdf_text,
)
from src.steam.detector import SteamDetector, steam_detector
from src.steam.acf_builder import ACFBuilder
from src.steam.depotcache_manager import DepotCacheManager
from src.steam.key_injector import KeyInjector
from src.steam.process_manager import SteamProcessManager, steam_process_manager

__all__ = [
    "parse_vdf_text",
    "parse_vdf_file",
    "dump_vdf_text",
    "dump_vdf_file",
    "SteamDetector",
    "steam_detector",
    "ACFBuilder",
    "DepotCacheManager",
    "KeyInjector",
    "SteamProcessManager",
    "steam_process_manager",
]
