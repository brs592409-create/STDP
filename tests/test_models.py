"""Unit tests for core models (AppInfo, DepotInfo, GamePackage, LibraryFolder, etc.)."""

from pathlib import Path
from src.core.models import (
    AppInfo,
    DepotInfo,
    GamePackage,
    LibraryFolder,
    ManifestFile,
    SystemHealth,
)


def test_depot_info_key_validation():
    valid_key = "a" * 64
    invalid_key_short = "a" * 63
    invalid_key_chars = "g" * 64

    depot_valid = DepotInfo(depot_id=1001, depot_key=valid_key)
    assert depot_valid.is_valid_key is True

    depot_short = DepotInfo(depot_id=1002, depot_key=invalid_key_short)
    assert depot_short.is_valid_key is False

    depot_invalid_chars = DepotInfo(depot_id=1003, depot_key=invalid_key_chars)
    assert depot_invalid_chars.is_valid_key is False

    depot_none = DepotInfo(depot_id=1004)
    assert depot_none.is_valid_key is False


def test_manifest_file():
    mf = ManifestFile(
        file_path=Path("dummy/path/100_200.manifest"),
        depot_id=100,
        manifest_id="200",
        size_bytes=1024,
    )
    assert mf.standard_filename == "100_200.manifest"
    assert mf.size_bytes == 1024


def test_app_info_computations():
    depots = [
        DepotInfo(depot_id=101, manifest_id="901", size_bytes=1000),
        DepotInfo(depot_id=102, manifest_id="902", size_bytes=2500),
    ]
    app = AppInfo(
        app_id=100,
        name='Cyberpunk 2077: Phantom / Liberty <Edition>*',
        depots=depots,
    )

    assert app.total_size_bytes == 3500
    # Check filename sanitization removes : / < > *
    assert ":" not in app.safe_install_dir
    assert "<" not in app.safe_install_dir
    assert "*" not in app.safe_install_dir
    assert app.get_depot(101) == depots[0]
    assert app.get_depot(999) is None


def test_game_package():
    app = AppInfo(app_id=500, name="Portal 2")
    pkg = GamePackage(
        app_info=app,
        lua_scripts={"500.lua": "addappid(500, 1, 'Portal 2')"},
        status="ready",
    )
    assert pkg.app_info.app_id == 500
    assert pkg.status == "ready"
    assert "500.lua" in pkg.lua_scripts


def test_library_folder_computations():
    total_bytes = 100 * (1024 ** 3)  # 100 GB
    free_bytes = 40 * (1024 ** 3)    # 40 GB
    folder = LibraryFolder(
        folder_id=1,
        path=Path("D:/SteamLibrary"),
        total_bytes=total_bytes,
        free_bytes=free_bytes,
        apps={100: 5000},
    )

    assert folder.total_gb == 100.0
    assert folder.free_gb == 40.0
    assert folder.usage_percent == 60.0
    assert "40.0 GB Free" in folder.display_text


def test_system_health():
    health = SystemHealth(
        steam_installed=True,
        depotcache_writable=True,
        issues=[],
    )
    assert health.is_healthy is True

    unhealthy = SystemHealth(
        steam_installed=True,
        depotcache_writable=False,
        issues=["Permission denied"],
    )
    assert unhealthy.is_healthy is False
