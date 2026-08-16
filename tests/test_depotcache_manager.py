"""Unit tests for DepotCacheManager."""

from pathlib import Path
from src.steam.depotcache_manager import DepotCacheManager


def test_depotcache_save_and_verify(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    manager = DepotCacheManager(steam_dir)

    content = b"TEST_MANIFEST_CONTENT_12345"
    depot_id = 1001
    manifest_id = "889977665544"

    # Save bytes
    saved_path = manager.save_manifest(depot_id, manifest_id, content)
    assert saved_path.exists()
    assert saved_path.name == "1001_889977665544.manifest"
    assert saved_path.read_bytes() == content

    # Check existence
    assert manager.has_manifest(depot_id, manifest_id) is True
    assert manager.has_manifest(9999, "0000") is False

    # Verify checksum
    expected_sha = manager.calculate_sha256(saved_path)
    assert manager.verify_manifest(depot_id, manifest_id, expected_sha) is True
    assert manager.verify_manifest(depot_id, manifest_id, "invalidhash") is False


def test_depotcache_list_manifests(tmp_path: Path):
    steam_dir = tmp_path / "Steam"
    manager = DepotCacheManager(steam_dir)

    manager.save_manifest(101, "111", b"data1")
    manager.save_manifest(102, "222", b"data2")
    # Non-manifest file in folder
    (steam_dir / "depotcache" / "other.txt").write_text("hello", encoding="utf-8")

    manifest_list = manager.list_installed_manifests()
    assert len(manifest_list) == 2
    depot_ids = {m.depot_id for m in manifest_list}
    assert depot_ids == {101, 102}


def test_depotcache_parse_filename():
    res = DepotCacheManager.parse_filename("1091501_8472918392817281920.manifest")
    assert res == (1091501, "8472918392817281920")

    assert DepotCacheManager.parse_filename("invalid_manifest.txt") is None
    assert DepotCacheManager.parse_filename("abc_def.manifest") is None
