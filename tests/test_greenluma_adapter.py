"""Unit tests for GreenLumaAdapter."""

from pathlib import Path
from src.core.models import AppInfo, DepotInfo
from src.unlockers.greenluma_adapter import GreenLumaAdapter


def test_greenluma_install_and_inject(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    adapter = GreenLumaAdapter()

    assert adapter.is_installed(steam_dir) is False
    assert adapter.install_hook(steam_dir) is True
    assert adapter.is_installed(steam_dir) is True

    app = AppInfo(
        app_id=500,
        name="Portal 2",
        depots=[DepotInfo(depot_id=501), DepotInfo(depot_id=502)],
    )

    assert adapter.inject_game(steam_dir, app) is True

    applist_dir = steam_dir / "AppList"
    assert (applist_dir / "0.txt").read_text(encoding="utf-8").strip() == "500"
    assert (applist_dir / "1.txt").read_text(encoding="utf-8").strip() == "501"
    assert (applist_dir / "2.txt").read_text(encoding="utf-8").strip() == "502"

    assert adapter.list_injected_games(steam_dir) == [500, 501, 502]

    # Remove 500
    assert adapter.remove_game(steam_dir, 500) is True
    assert adapter.list_injected_games(steam_dir) == [501, 502]
    # Check gapless re-indexing
    assert (applist_dir / "0.txt").read_text(encoding="utf-8").strip() == "501"
    assert (applist_dir / "1.txt").read_text(encoding="utf-8").strip() == "502"
    assert not (applist_dir / "2.txt").exists()
