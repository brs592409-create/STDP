"""Unit tests for SteamToolsAdapter."""

from pathlib import Path
from src.core.models import AppInfo, DepotInfo, GamePackage
from src.unlockers.steamtools_adapter import SteamToolsAdapter


def test_steamtools_installation_and_injection(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    adapter = SteamToolsAdapter()

    assert adapter.is_installed(steam_dir) is False

    # Install
    assert adapter.install_hook(steam_dir) is True
    assert adapter.is_installed(steam_dir) is True

    # Inject Game
    depots = [
        DepotInfo(
            depot_id=1091501,
            depot_key="11223344556677889900AABBCCDDEEFF11223344556677889900AABBCCDDEEFF",
            name="Main Content",
        )
    ]
    app = AppInfo(app_id=1091500, name="Cyberpunk 2077", depots=depots)

    assert adapter.inject_game(steam_dir, app) is True

    # Verify files created in all steam subdirectories
    for d in ["config/st_scripts", "st_scripts", "lua", "steamtools/lua"]:
        lua_file = steam_dir / d / "1091500.lua"
        assert lua_file.exists(), f"{d} does not contain 1091500.lua"
        content = lua_file.read_text(encoding="utf-8")
        assert "addappid(1091500" in content
        assert "setdepotkey(1091501" in content

    # List
    injected = adapter.list_injected_games(steam_dir)
    assert 1091500 in injected

    # Remove
    assert adapter.remove_game(steam_dir, 1091500) is True
    for d in ["config/st_scripts", "st_scripts", "lua", "steamtools/lua"]:
        lua_file = steam_dir / d / "1091500.lua"
        assert not lua_file.exists()
    assert 1091500 not in adapter.list_injected_games(steam_dir)


def test_steamtools_custom_package_lua(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    adapter = SteamToolsAdapter()

    custom_script = '-- Custom LUA Script\naddappid(730, 1, "CS2")\n'
    app = AppInfo(app_id=730, name="CS2")
    pkg = GamePackage(app_info=app, lua_scripts={"730.lua": custom_script})

    assert adapter.inject_game(steam_dir, app, package=pkg) is True
    lua_file = steam_dir / "config" / "st_scripts" / "730.lua"
    assert lua_file.exists()
    assert lua_file.read_text(encoding="utf-8") == custom_script
