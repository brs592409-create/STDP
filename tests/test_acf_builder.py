"""Unit tests for ACF builder and merger."""

from pathlib import Path
from src.core.models import AppInfo, DepotInfo
from src.steam.acf_builder import ACFBuilder
from src.steam.vdf_parser import parse_vdf_file, dump_vdf_file


def test_build_acf_data_ready_to_install():
    depots = [
        DepotInfo(depot_id=1091501, manifest_id="8472918392817281920", size_bytes=70000000),
        DepotInfo(depot_id=1091502, manifest_id="1234567890123456789", size_bytes=30000000),
    ]
    app = AppInfo(app_id=1091500, name="Cyberpunk 2077", depots=depots)

    # StateFlags is "1026" by default with BytesDownloaded "0" to indicate download needed
    data = ACFBuilder.build_acf_data(app)
    app_state = data["AppState"]

    assert app_state["appid"] == "1091500"
    assert app_state["name"] == "Cyberpunk 2077"
    assert app_state["StateFlags"] == "1026"
    assert app_state["BytesToDownload"] == "100000000"
    assert app_state["BytesDownloaded"] == "0"
    assert "1091501" in app_state["InstalledDepots"]
    assert app_state["InstalledDepots"]["1091501"]["manifest"] == "8472918392817281920"


def test_build_acf_data_custom_state_flags():
    depots = [
        DepotInfo(depot_id=1091501, manifest_id="8472918392817281920", size_bytes=70000000),
    ]
    app = AppInfo(app_id=1091500, name="Cyberpunk 2077", depots=depots)

    data = ACFBuilder.build_acf_data(app, state_flags=6)
    app_state = data["AppState"]

    assert app_state["StateFlags"] == "6"
    assert app_state["BytesDownloaded"] == "0"


def test_write_and_merge_acf(tmp_path: Path):
    library_dir = tmp_path / "SteamLibrary"
    depots_v1 = [
        DepotInfo(depot_id=101, manifest_id="111111", size_bytes=5000),
    ]
    app_v1 = AppInfo(app_id=500, name="Test Game", depots=depots_v1)

    # 1. Write initial ACF
    acf_path = ACFBuilder.write_acf(app_v1, library_dir)
    assert acf_path.exists()

    parsed_v1 = parse_vdf_file(acf_path)
    assert parsed_v1["AppState"]["appid"] == "500"
    assert parsed_v1["AppState"]["StateFlags"] == "1026"
    assert parsed_v1["AppState"]["BytesDownloaded"] == "0"
    assert "101" in parsed_v1["AppState"]["InstalledDepots"]

    # 2. Add DLC depot and write with merge
    depots_v2 = [
        DepotInfo(depot_id=101, manifest_id="111111", size_bytes=5000),
        DepotInfo(depot_id=102, manifest_id="222222", size_bytes=7000),
    ]
    app_v2 = AppInfo(app_id=500, name="Test Game", depots=depots_v2)

    ACFBuilder.write_acf(app_v2, library_dir, merge_if_exists=True, backup_existing=True)

    # Check backup exists
    backup_file = acf_path.parent / "appmanifest_500.acf.bak"
    assert backup_file.exists()

    # Check merged ACF contains both depots
    parsed_v2 = parse_vdf_file(acf_path)
    installed = parsed_v2["AppState"]["InstalledDepots"]
    assert "101" in installed
    assert "102" in installed
    assert installed["102"]["manifest"] == "222222"
    assert parsed_v2["AppState"]["BytesToDownload"] == "12000"
    assert parsed_v2["AppState"]["BytesDownloaded"] == "0"


def test_register_in_libraryfolders(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    steamapps = steam_dir / "steamapps"
    steamapps.mkdir(parents=True)

    vdf_file = steamapps / "libraryfolders.vdf"
    initial_vdf = {
        "libraryfolders": {
            "0": {
                "path": str(steam_dir),
                "apps": {},
            }
        }
    }
    dump_vdf_file(vdf_file, initial_vdf)

    # Register app 1091500
    res = ACFBuilder.register_in_libraryfolders(steam_dir, steam_dir, 1091500, 70000000)
    assert res is True

    updated_data = parse_vdf_file(vdf_file)
    assert "1091500" in updated_data["libraryfolders"]["0"]["apps"]
    assert updated_data["libraryfolders"]["0"]["apps"]["1091500"] == "70000000"
