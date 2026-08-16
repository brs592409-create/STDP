"""Core data models for STDP using Pydantic."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, computed_field


class DepotInfo(BaseModel):
    """Represents a single Steam game depot."""

    depot_id: int
    manifest_id: Optional[str] = None
    depot_key: Optional[str] = None
    manifest_url: Optional[str] = None
    size_bytes: int = 0
    depot_type: str = "base"  # base, dlc, language, workshop, optional
    name: Optional[str] = None

    @property
    def is_valid_key(self) -> bool:
        """Check if depot key is a valid 64-char hex string."""
        if not self.depot_key:
            return False
        clean_key = self.depot_key.strip()
        return len(clean_key) == 64 and all(c in "0123456789abcdefABCDEF" for c in clean_key)


class ManifestFile(BaseModel):
    """Represents a local or target manifest file."""

    file_path: Path
    depot_id: int
    manifest_id: str
    sha256_hash: Optional[str] = None
    size_bytes: int = 0

    @property
    def standard_filename(self) -> str:
        """Return standardized filename: <depot_id>_<manifest_id>.manifest"""
        return f"{self.depot_id}_{self.manifest_id}.manifest"


class AppInfo(BaseModel):
    """Represents a Steam game/application."""

    app_id: int
    name: str
    thumbnail_url: Optional[str] = None
    header_url: Optional[str] = None
    depots: List[DepotInfo] = Field(default_factory=list)
    lua_script_url: Optional[str] = None
    lua_content: Optional[str] = None
    install_dir_name: Optional[str] = None

    @computed_field
    @property
    def total_size_bytes(self) -> int:
        """Total size of all depots in bytes."""
        return sum(depot.size_bytes for depot in self.depots)

    @computed_field
    @property
    def safe_install_dir(self) -> str:
        """Sanitized directory name for installation."""
        if self.install_dir_name:
            return self.install_dir_name
        # Remove invalid Windows folder characters: <>:"/\|?*
        invalid_chars = '<>:"/\\|?*'
        sanitized = "".join(c for c in self.name if c not in invalid_chars).strip()
        return sanitized or f"App_{self.app_id}"

    def get_depot(self, depot_id: int) -> Optional[DepotInfo]:
        """Find a depot by its depot_id."""
        for d in self.depots:
            if d.depot_id == depot_id:
                return d
        return None


class GamePackage(BaseModel):
    """Represents an extracted or downloaded package ready for injection."""

    app_info: AppInfo
    manifests: List[ManifestFile] = Field(default_factory=list)
    lua_scripts: Dict[str, str] = Field(default_factory=dict)  # filename -> script content
    source_archive: Optional[Path] = None
    status: str = "pending"  # pending, extracting, downloading, ready, installed, error
    error_message: Optional[str] = None


class LibraryFolder(BaseModel):
    """Represents a Steam library folder location on disk."""

    folder_id: int
    path: Path
    label: str = ""
    total_bytes: int = 0
    free_bytes: int = 0
    apps: Dict[int, int] = Field(default_factory=dict)  # app_id -> size_bytes
    mounted: bool = True

    @computed_field
    @property
    def free_gb(self) -> float:
        """Free space in Gigabytes."""
        return round(self.free_bytes / (1024 ** 3), 2)

    @computed_field
    @property
    def total_gb(self) -> float:
        """Total space in Gigabytes."""
        return round(self.total_bytes / (1024 ** 3), 2)

    @computed_field
    @property
    def usage_percent(self) -> float:
        """Disk usage percentage."""
        if self.total_bytes == 0:
            return 0.0
        used = self.total_bytes - self.free_bytes
        return round((used / self.total_bytes) * 100, 1)

    @property
    def display_text(self) -> str:
        """Formatted string for UI selectors: 'D:\\SteamLibrary (420.5 GB Free)'"""
        return f"{self.path} ({self.free_gb:.1f} GB Free)"


class SystemHealth(BaseModel):
    """Represents system health diagnosis and Steam environment status."""

    steam_installed: bool = False
    steam_path: Optional[Path] = None
    steam_running: bool = False
    steam_pid: Optional[int] = None
    is_admin: bool = False
    depotcache_writable: bool = False
    libraries_found: List[LibraryFolder] = Field(default_factory=list)
    active_hook_installed: bool = False
    unlocker_installed: bool = False
    unlocker_running: bool = False
    issues: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def is_healthy(self) -> bool:
        """Returns True if no critical issues exist and Steam is installed."""
        return self.steam_installed and self.depotcache_writable and len(self.issues) == 0
