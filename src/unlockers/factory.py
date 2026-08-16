"""Factory and registry for unlocker adapters."""

from __future__ import annotations

from typing import Dict, List, Optional

from src.unlockers.base import UnlockerAdapter
from src.unlockers.steamtools_adapter import SteamToolsAdapter

_REGISTRY: Dict[str, UnlockerAdapter] = {
    "steamtools": SteamToolsAdapter(),
}


def get_unlocker(identifier: str) -> Optional[UnlockerAdapter]:
    """Retrieve an unlocker adapter by its unique identifier."""
    return _REGISTRY.get(identifier.lower().strip())


def list_unlockers() -> List[UnlockerAdapter]:
    """List all registered unlocker adapters."""
    return list(_REGISTRY.values())


def register_unlocker(adapter: UnlockerAdapter) -> None:
    """Register a new custom unlocker adapter."""
    _REGISTRY[adapter.identifier.lower().strip()] = adapter
