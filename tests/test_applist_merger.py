"""Unit tests for GreenLuma AppList smart merge and collision prevention."""

from pathlib import Path
from src.core.models import AppInfo, DepotInfo
from src.unlockers.greenluma_adapter import GreenLumaAdapter


def test_applist_smart_merge_preserves_existing(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    applist_dir = steam_dir / "AppList"
    applist_dir.mkdir(parents=True)

    # 1. Simulate existing user configuration with 3 games
    (applist_dir / "0.txt").write_text("100\n", encoding="utf-8")
    (applist_dir / "1.txt").write_text("101\n", encoding="utf-8")
    (applist_dir / "2.txt").write_text("200\n", encoding="utf-8")

    adapter = GreenLumaAdapter()

    # 2. Inject a new game with AppID 300 and depot 301
    new_game = AppInfo(
        app_id=300,
        name="New Game",
        depots=[DepotInfo(depot_id=301)],
    )

    assert adapter.inject_game(steam_dir, new_game) is True

    # 3. Verify existing files remain intact
    assert (applist_dir / "0.txt").read_text(encoding="utf-8").strip() == "100"
    assert (applist_dir / "1.txt").read_text(encoding="utf-8").strip() == "101"
    assert (applist_dir / "2.txt").read_text(encoding="utf-8").strip() == "200"

    # 4. Verify new sequential files were written starting at 3.txt
    assert (applist_dir / "3.txt").read_text(encoding="utf-8").strip() == "300"
    assert (applist_dir / "4.txt").read_text(encoding="utf-8").strip() == "301"

    # 5. Verify backup was created
    backup_dir = steam_dir / "AppList_backup"
    assert backup_dir.exists()
    assert (backup_dir / "0.txt").exists()


def test_applist_duplicate_id_prevention(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    applist_dir = steam_dir / "AppList"
    applist_dir.mkdir(parents=True)

    # Pre-existing entry 400
    (applist_dir / "0.txt").write_text("400\n", encoding="utf-8")

    adapter = GreenLumaAdapter()
    game_with_duplicate = AppInfo(
        app_id=400,
        name="Game 400",
        depots=[DepotInfo(depot_id=401)],
    )

    assert adapter.inject_game(steam_dir, game_with_duplicate) is True

    # Only 401 should be appended as 1.txt since 400 was already present
    assert (applist_dir / "0.txt").read_text(encoding="utf-8").strip() == "400"
    assert (applist_dir / "1.txt").read_text(encoding="utf-8").strip() == "401"
    assert not (applist_dir / "2.txt").exists()
