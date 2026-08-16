"""Abstract base class for Steam unlocker / hook adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

from src.core.models import AppInfo, GamePackage


class UnlockerAdapter(ABC):
    """Abstract interface that all unlocker mechanisms (SteamTools, GreenLuma, etc.) must implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable display name of the adapter."""
        pass

    @property
    @abstractmethod
    def identifier(self) -> str:
        """Unique machine-friendly identifier (e.g. 'steamtools', 'greenluma')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short summary of how this unlocker operates."""
        pass

    @abstractmethod
    def is_installed(self, steam_path: Union[Path, str]) -> bool:
        """Check if the unlocker directory/hook files exist in the target Steam installation."""
        pass

    @abstractmethod
    def install_hook(self, steam_path: Union[Path, str]) -> bool:
        """Install necessary directories or hook loader files into Steam."""
        pass

    @abstractmethod
    def uninstall_hook(self, steam_path: Union[Path, str]) -> bool:
        """Safely remove the unlocker files from Steam."""
        pass

    @abstractmethod
    def inject_game(
        self,
        steam_path: Union[Path, str],
        app_info: AppInfo,
        package: Optional[GamePackage] = None,
    ) -> bool:
        """Inject game credentials, AppID, DLCs, and depot keys into the unlocker."""
        pass

    @abstractmethod
    def remove_game(self, steam_path: Union[Path, str], app_id: int) -> bool:
        """Remove a previously injected game from the unlocker system."""
        pass

    @abstractmethod
    def list_injected_games(self, steam_path: Union[Path, str]) -> List[int]:
        """List all AppIDs currently registered with this unlocker."""
        pass
