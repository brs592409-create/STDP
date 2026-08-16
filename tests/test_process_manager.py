"""Unit tests for SteamProcessManager."""

from unittest.mock import MagicMock, patch
from pathlib import Path
from src.steam.process_manager import SteamProcessManager


def test_is_running_mock():
    with patch.object(SteamProcessManager, "get_steam_process") as mock_get_proc:
        mock_get_proc.return_value = None
        assert SteamProcessManager.is_running() is False
        assert SteamProcessManager.get_pid() is None

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_get_proc.return_value = mock_proc
        assert SteamProcessManager.is_running() is True
        assert SteamProcessManager.get_pid() == 12345


def test_shutdown_when_already_stopped():
    with patch.object(SteamProcessManager, "is_running", return_value=False):
        assert SteamProcessManager.shutdown_steam(timeout_seconds=1) is True


def test_start_steam_executable_not_found(tmp_path: Path):
    fake_steam_path = tmp_path / "NonExistentSteam"
    assert SteamProcessManager.start_steam(steam_path=fake_steam_path) is False


def test_trigger_install():
    with patch("os.startfile", create=True) as mock_startfile:
        assert SteamProcessManager.trigger_install(12345) is True
        mock_startfile.assert_called_once_with("steam://install/12345")


def test_trigger_nav_game():
    with patch("os.startfile", create=True) as mock_startfile:
        assert SteamProcessManager.trigger_nav_game(12345) is True
        mock_startfile.assert_called_once_with("steam://nav/games/details/12345")


def test_trigger_validate():
    with patch("os.startfile", create=True) as mock_startfile:
        assert SteamProcessManager.trigger_validate(12345) is True
        mock_startfile.assert_called_once_with("steam://validate/12345")


def test_trigger_open_library():
    with patch("os.startfile", create=True) as mock_startfile:
        assert SteamProcessManager.trigger_open_library() is True
        mock_startfile.assert_called_once_with("steam://open/games")


