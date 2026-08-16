"""Unit tests for KeyInjector."""

from pathlib import Path
from src.core.models import AppInfo, DepotInfo
from src.steam.key_injector import KeyInjector
from src.steam.vdf_parser import dump_vdf_file, parse_vdf_file


def test_key_validation():
    valid = "0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF"
    assert KeyInjector.is_valid_hex_key(valid) is True
    assert KeyInjector.is_valid_hex_key(valid.lower()) is True
    assert KeyInjector.is_valid_hex_key("SHORTKEY") is False
    assert KeyInjector.is_valid_hex_key(None) is False


def test_generate_and_parse_lua_script():
    key_1 = "1111111111111111111111111111111111111111111111111111111111111111"
    key_2 = "2222222222222222222222222222222222222222222222222222222222222222"

    depots = [
        DepotInfo(depot_id=1001, name="Base Game", depot_key=key_1),
        DepotInfo(depot_id=1002, name="Soundtrack", depot_key=key_2),
        DepotInfo(depot_id=1003, name="Artbook", depot_key=None),
    ]
    app = AppInfo(app_id=1000, name="Awesome Game", depots=depots)

    lua_code = KeyInjector.generate_lua_script(app)
    assert 'addappid(1000, 1, "Awesome Game")' in lua_code
    assert 'addappid(1001, 1, "Base Game")' in lua_code
    assert 'addappid(1002, 1, "Soundtrack")' in lua_code
    assert 'addappid(1003, 1, "Artbook")' in lua_code
    assert f'setdepotkey(1001, "{key_1}")' in lua_code
    assert f'setdepotkey(1002, "{key_2}")' in lua_code

    # Test reverse parsing
    parsed_keys = KeyInjector.parse_lua_depot_keys(lua_code)
    assert parsed_keys[1001] == key_1
    assert parsed_keys[1002] == key_2
    assert 1003 not in parsed_keys


def test_generate_lua_script_escaping():
    app = AppInfo(
        app_id=2000,
        name='Game "Special" Edition\nBonus',
        depots=[
            DepotInfo(depot_id=2001, name='DLC "Pack" 1', depot_key="AA"*32)
        ],
    )
    lua_code = KeyInjector.generate_lua_script(app)
    assert 'addappid(2000, 1, "Game \\"Special\\" Edition Bonus")' in lua_code
    assert 'addappid(2001, 1, "DLC \\"Pack\\" 1")' in lua_code
    assert f'setdepotkey(2001, "{"AA"*32}")' in lua_code


def test_inject_depot_keys_to_config_vdf(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    config_dir = steam_dir / "config"
    config_dir.mkdir(parents=True)

    config_vdf = config_dir / "config.vdf"
    dump_vdf_file(config_vdf, {"Software": {"Valve": {"Steam": {}}}})

    key = "11223344556677889900AABBCCDDEEFF11223344556677889900AABBCCDDEEFF"
    depot = DepotInfo(depot_id=1091501, depot_key=key)
    app = AppInfo(app_id=1091500, name="Cyberpunk 2077", depots=[depot])

    res = KeyInjector.inject_depot_keys_to_config_vdf(steam_dir, app)
    assert res is True

    data = parse_vdf_file(config_vdf)
    depots = data["Software"]["Valve"]["Steam"]["depots"]
    assert "1091501" in depots
    assert depots["1091501"]["DecryptionKey"] == key
