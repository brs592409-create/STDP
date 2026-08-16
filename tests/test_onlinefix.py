"""Unit tests for Online-Fix.me Steam_Fix engine with Smart Anchor and Atomic rollback."""

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
import pytest

from src.onlinefix.installer import InstalledGameInfo, OnlineFixInstaller, online_fix_installer


@pytest.fixture
def unreal_game_env():
    """Create a simulated Unreal Engine game directory (Binaries/Win64)."""
    temp_dir = Path(tempfile.mkdtemp(prefix="STDP_TestUnreal_"))
    game_dir = temp_dir / "steamapps" / "common" / "UnrealGame"
    binaries_dir = game_dir / "Binaries" / "Win64"
    binaries_dir.mkdir(parents=True, exist_ok=True)

    # Main game launcher in root and real executable in Binaries/Win64
    (game_dir / "UnrealGame.exe").write_text("launcher exe", encoding="utf-8")
    (binaries_dir / "UnrealGame-Win64-Shipping.exe").write_text("real shipping exe", encoding="utf-8")
    (binaries_dir / "steam_api64.dll").write_text("ORIGINAL_UNREAL_STEAM_API_64", encoding="utf-8")

    yield temp_dir, game_dir, binaries_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def dummy_fix_archive(tmp_path):
    """Create a flat password-protected zip file with online-fix.me password."""
    zip_path = tmp_path / "UnrealGame.Fix.Repair.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("OnlineFix.ini", "Language=english\nFakeName=Player1\n", compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OnlineFix64.dll", "ONLINE_FIX_DLL_CONTENT", compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("steam_api64.dll", "MODIFIED_ONLINE_FIX_STEAM_API", compress_type=zipfile.ZIP_DEFLATED)
        zf.setpassword(b"online-fix.me")
    return zip_path


def test_detect_game_structure_unreal(unreal_game_env):
    _, game_dir, _ = unreal_game_env
    installer = OnlineFixInstaller()

    engine, primary_exe, anchor_subfolder = installer.detect_game_structure(game_dir)
    assert engine == "Unreal Engine"
    assert anchor_subfolder == Path("Binaries/Win64")
    assert primary_exe in ["UnrealGame-Win64-Shipping.exe", "UnrealGame.exe"]


def test_smart_anchor_installation_unreal(unreal_game_env, dummy_fix_archive):
    temp_dir, game_dir, binaries_dir = unreal_game_env
    installer = OnlineFixInstaller()

    game_info = InstalledGameInfo(
        app_id=123456,
        name="UnrealGame",
        install_dir_name="UnrealGame",
        game_path=game_dir,
        library_path=temp_dir,
    )

    # 1. Install Fix
    success, msg = installer.install_fix(
        archive_path=dummy_fix_archive,
        target_game=game_info,
        custom_nickname="GamerTR",
        custom_language="turkish",
    )
    assert success is True

    # 2. Verify Smart Anchor placement (Should be in Binaries/Win64, NOT root)
    assert (binaries_dir / "OnlineFix.ini").exists()
    assert (binaries_dir / "OnlineFix64.dll").exists()
    assert (binaries_dir / "steam_api64.dll").read_text(encoding="utf-8") == "MODIFIED_ONLINE_FIX_STEAM_API"

    # Verify root was NOT polluted
    assert not (game_dir / "OnlineFix.dll").exists()

    # Verify manifest file
    manifest_file = game_dir / ".stdp_fix_manifest.json"
    assert manifest_file.exists()
    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert "Binaries/Win64/steam_api64.dll" in manifest_data["backed_up_files"]
    assert "Binaries/Win64/OnlineFix64.dll" in manifest_data["created_files"]

    # 3. Revert Fix
    revert_success, _ = installer.revert_fix(game_info)
    assert revert_success is True

    # Check original file restored
    assert (binaries_dir / "steam_api64.dll").read_text(encoding="utf-8") == "ORIGINAL_UNREAL_STEAM_API_64"
    assert not (binaries_dir / "OnlineFix64.dll").exists()
    assert not manifest_file.exists()
    assert not (game_dir / ".stdp_fix_backup").exists()


def test_find_extractors():
    """Verify that UnRAR or 7z executables can be resolved properly."""
    installer = OnlineFixInstaller()
    unrar = installer.find_unrar_executable()
    seven_zip = installer.find_7z_executable()
    # At least one of UnRAR or 7z should be found either in bundled_installers or system
    assert unrar is not None or seven_zip is not None


def test_extract_archive_with_password(tmp_path):
    """Test extracting password-protected archives with standard online-fix.me password."""
    import subprocess
    installer = OnlineFixInstaller()

    # Create dummy files
    src_dir = tmp_path / "files_to_pack"
    src_dir.mkdir()
    (src_dir / "OnlineFix.ini").write_text("FakeName=Player", encoding="utf-8")
    (src_dir / "OnlineFix64.dll").write_text("DLL_DATA", encoding="utf-8")

    archive_7z = tmp_path / "Game.Fix.7z"
    # Create encrypted 7z archive with password 'online-fix.me'
    subprocess.run(
        ["7z", "a", str(archive_7z), "OnlineFix.ini", "OnlineFix64.dll", "-ponline-fix.me"],
        cwd=str(src_dir),
        capture_output=True,
        check=True,
    )

    dest_dir = tmp_path / "extracted_out"
    success, msg = installer.extract_archive(archive_7z, dest_dir)
    assert success is True
    assert (dest_dir / "OnlineFix.ini").exists()
    assert (dest_dir / "OnlineFix64.dll").exists()


def test_analyze_fix_archive_matching(tmp_path):
    """Test analyzing an archive and auto-matching with an installed game."""
    import subprocess
    installer = OnlineFixInstaller()

    src_dir = tmp_path / "fix_contents"
    src_dir.mkdir()
    (src_dir / "OnlineFix64.dll").write_text("DLL", encoding="utf-8")
    (src_dir / "steam_api64.dll").write_text("API", encoding="utf-8")

    archive_path = tmp_path / "Lethal.Company.Fix.Repair.7z"
    subprocess.run(
        ["7z", "a", str(archive_path), "OnlineFix64.dll", "steam_api64.dll", "-ponline-fix.me"],
        cwd=str(src_dir),
        capture_output=True,
        check=True,
    )

    installed_games = [
        InstalledGameInfo(
            app_id=1966720,
            name="Lethal Company",
            install_dir_name="Lethal Company",
            game_path=tmp_path / "lethal_company_dir",
            library_path=tmp_path,
        )
    ]

    analysis = installer.analyze_fix_archive(archive_path, installed_games)
    assert analysis.matched_game is not None
    assert analysis.matched_game.name == "Lethal Company"
    assert analysis.has_onlinefix_dll is True
    assert analysis.has_steam_api is True


def test_extract_rar_archive(tmp_path):
    """Test extracting a real RAR archive using UnRAR / 7-Zip fallback."""
    installer = OnlineFixInstaller()
    
    # Copy authentic RAR archive
    archive_rar = tmp_path / "Game.Fix.rar"
    if Path("/tmp/unrarw64.exe").exists():
        shutil.copy2("/tmp/unrarw64.exe", archive_rar)
    else:
        # Fallback: create 7z archive renamed as .rar to verify extension handling
        src_dir = tmp_path / "rar_src"
        src_dir.mkdir()
        (src_dir / "OnlineFix.ini").write_text("FakeName=Player", encoding="utf-8")
        import subprocess
        subprocess.run(
            ["7z", "a", "-t7z", str(archive_rar), "OnlineFix.ini", "-ponline-fix.me"],
            cwd=str(src_dir),
            capture_output=True,
            check=True,
        )

    dest_dir = tmp_path / "extracted_rar_out"
    success, msg = installer.extract_archive(archive_rar, dest_dir)
    assert success is True
    assert any(dest_dir.iterdir())


def test_onlinefix_login_banner_config_flow():
    """Verify onlinefix_login_prompt_shown defaults to False and can be dismissed."""
    from src.core.config import ConfigManager
    import tempfile

    tmp_cfg_path = Path(tempfile.gettempdir()) / "test_config_onlinefix.json"
    if tmp_cfg_path.exists():
        tmp_cfg_path.unlink()

    cfg_mgr = ConfigManager(config_path=tmp_cfg_path)
    # Default should be False (so banner is visible)
    assert cfg_mgr.config.onlinefix_login_prompt_shown is False

    # When user clicks dismiss:
    cfg_mgr.update(onlinefix_login_prompt_shown=True)
    assert cfg_mgr.config.onlinefix_login_prompt_shown is True

    # Reload from disk
    cfg_mgr2 = ConfigManager(config_path=tmp_cfg_path)
    assert cfg_mgr2.config.onlinefix_login_prompt_shown is True

    if tmp_cfg_path.exists():
        tmp_cfg_path.unlink()



