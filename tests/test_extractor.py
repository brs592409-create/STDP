"""Unit tests for ArchiveExtractor."""

import zipfile
from pathlib import Path
from src.depotbox.extractor import ArchiveExtractor


def test_extract_scenario_a_standard_zip(tmp_path: Path):
    """Scenario A: Standard Depotbox package with manifest and lua in root."""
    zip_file = tmp_path / "Cyberpunk_1091500.zip"
    key = "11223344556677889900AABBCCDDEEFF11223344556677889900AABBCCDDEEFF"
    lua_code = f'addappid(1091500, 1, "Cyberpunk 2077")\nsetdepotkey(1091501, "{key}")\n'

    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("1091501_8472918392817281920.manifest", b"MANIFEST_CHUNK_DATA_ABC")
        zf.writestr("1091500.lua", lua_code)

    extractor = ArchiveExtractor(extract_root=tmp_path / "extracted")
    pkg = extractor.extract_package(zip_file)

    assert pkg.app_info.app_id == 1091500
    assert pkg.app_info.name == "Cyberpunk 2077"
    assert len(pkg.manifests) == 1
    assert pkg.manifests[0].depot_id == 1091501
    assert pkg.manifests[0].manifest_id == "8472918392817281920"
    assert len(pkg.app_info.depots) == 1
    assert pkg.app_info.depots[0].depot_key == key


def test_extract_scenario_b_steamtools_structure_zip(tmp_path: Path):
    """Scenario B: SteamTools nested structure (depotcache/ and st_scripts/)."""
    zip_file = tmp_path / "Portal2_Package.zip"
    lua_code = 'addappid(500, 1, "Portal 2")\n'

    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("depotcache/501_111222333.manifest", b"PORTAL_DATA")
        zf.writestr("st_scripts/500.lua", lua_code)

    extractor = ArchiveExtractor(extract_root=tmp_path / "extracted")
    pkg = extractor.extract_package(zip_file)

    assert pkg.app_info.app_id == 500
    assert pkg.app_info.name == "Portal 2"
    assert len(pkg.manifests) == 1
    assert pkg.manifests[0].depot_id == 501
    assert pkg.manifests[0].manifest_id == "111222333"


def test_extract_single_manifest_file(tmp_path: Path):
    """Scenario C: Dropping a single raw .manifest file."""
    manifest_file = tmp_path / "731_99887766.manifest"
    manifest_file.write_bytes(b"CS2_DATA")

    extractor = ArchiveExtractor(extract_root=tmp_path / "extracted")
    pkg = extractor.extract_package(manifest_file)

    assert len(pkg.manifests) == 1
    assert pkg.manifests[0].depot_id == 731
    assert pkg.manifests[0].manifest_id == "99887766"


def test_extract_single_lua_file(tmp_path: Path):
    """Dropping a single raw .lua file."""
    lua_file = tmp_path / "1091500.lua"
    key = "AABBCCDDEEFF00112233445566778899AABBCCDDEEFF00112233445566778899"
    lua_file.write_text(f'addappid(1091500, 1, "Cyberpunk 2077")\nsetdepotkey(1091501, "{key}")\n', encoding="utf-8")

    extractor = ArchiveExtractor(extract_root=tmp_path / "extracted")
    pkg = extractor.extract_package(lua_file)

    assert pkg.app_info.app_id == 1091500
    assert pkg.app_info.name == "Cyberpunk 2077"
    assert len(pkg.app_info.depots) == 1
    assert pkg.app_info.depots[0].depot_id == 1091501
    assert pkg.app_info.depots[0].depot_key == key
