"""Unit tests for SteamDetector."""

from pathlib import Path
from src.steam.detector import SteamDetector
from src.steam.vdf_parser import dump_vdf_file


def test_detector_with_override_path(tmp_path: Path):
    steam_dir = tmp_path / "MockSteam"
    steam_dir.mkdir()
    (steam_dir / "steam.exe").write_text("", encoding="utf-8")

    detector = SteamDetector(override_steam_path=steam_dir)
    assert detector.find_steam_path() == steam_dir


def test_detector_libraryfolders_modern(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    steamapps_dir = steam_dir / "steamapps"
    steamapps_dir.mkdir(parents=True)

    extra_lib = tmp_path / "ExtraLibrary"
    extra_lib.mkdir()

    # Create modern libraryfolders.vdf
    vdf_data = {
        "libraryfolders": {
            "0": {
                "path": str(steam_dir),
                "label": "",
                "apps": {"730": "30000000"},
            },
            "1": {
                "path": str(extra_lib),
                "label": "Fast SSD",
                "apps": {"1091500": "70000000"},
            },
        }
    }
    dump_vdf_file(steamapps_dir / "libraryfolders.vdf", vdf_data)

    detector = SteamDetector(override_steam_path=steam_dir)
    folders = detector.get_library_folders(steam_dir)

    assert len(folders) == 2
    paths = [f.path.resolve() for f in folders]
    assert steam_dir.resolve() in paths
    assert extra_lib.resolve() in paths

    ssd_folder = next(f for f in folders if f.path.resolve() == extra_lib.resolve())
    assert ssd_folder.label == "Fast SSD"
    assert ssd_folder.apps.get(1091500) == 70000000


def test_system_health_check(tmp_path: Path):
    steam_dir = tmp_path / "HealthySteam"
    steam_dir.mkdir()
    (steam_dir / "steamapps").mkdir()
    (steam_dir / "depotcache").mkdir()

    detector = SteamDetector(override_steam_path=steam_dir)
    health = detector.check_system_health()

    assert health.steam_installed is True
    assert health.depotcache_writable is True
