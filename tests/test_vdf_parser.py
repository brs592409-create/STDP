"""Unit tests for Valve VDF KeyValues parsing and serialization."""

from pathlib import Path
import pytest
from src.steam.vdf_parser import (
    dump_vdf_file,
    dump_vdf_text,
    parse_vdf_file,
    parse_vdf_text,
)

SAMPLE_VDF_TEXT = '''
"AppState"
{
\t"appid"\t\t"1091500"
\t"Universe"\t\t"1"
\t"name"\t\t"Cyberpunk 2077"
\t"StateFlags"\t\t"4"
\t"InstalledDepots"
\t{
\t\t"1091501"
\t\t{
\t\t\t"manifest"\t\t"8472918392817281920"
\t\t\t"size"\t\t"73400320000"
\t\t}
\t}
}
'''


def test_parse_vdf_text():
    parsed = parse_vdf_text(SAMPLE_VDF_TEXT)
    assert "AppState" in parsed
    assert parsed["AppState"]["appid"] == "1091500"
    assert parsed["AppState"]["name"] == "Cyberpunk 2077"
    assert parsed["AppState"]["InstalledDepots"]["1091501"]["manifest"] == "8472918392817281920"


def test_dump_and_parse_roundtrip(tmp_path: Path):
    data = {
        "AppState": {
            "appid": "730",
            "name": "Counter-Strike 2",
            "StateFlags": "4",
            "InstalledDepots": {
                "731": {"manifest": "11223344", "size": "30000000000"}
            },
        }
    }

    dumped_text = dump_vdf_text(data)
    assert '"appid"' in dumped_text
    assert '"Counter-Strike 2"' in dumped_text

    file_path = tmp_path / "appmanifest_730.acf"
    dump_vdf_file(file_path, data)
    assert file_path.exists()

    reloaded = parse_vdf_file(file_path)
    assert reloaded["AppState"]["appid"] == "730"
    assert reloaded["AppState"]["name"] == "Counter-Strike 2"
    assert reloaded["AppState"]["InstalledDepots"]["731"]["manifest"] == "11223344"


def test_parse_empty_vdf():
    assert parse_vdf_text("") == {}
    assert parse_vdf_text("   \n\t") == {}


def test_parse_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        parse_vdf_file(Path("non_existent_file_path_123.acf"))
