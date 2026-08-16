"""Unit tests for DepotboxClient."""

from unittest.mock import MagicMock
from src.depotbox.client import DepotboxClient


def test_parse_json_app_info():
    client = DepotboxClient()
    sample_json = {
        "app_id": 1091500,
        "game_name": "Cyberpunk 2077",
        "thumbnail_url": "https://example.com/thumb.jpg",
        "depots": [
            {
                "depot_id": 1091501,
                "manifest_id": "8472918392817281920",
                "depot_key": "11223344556677889900AABBCCDDEEFF11223344556677889900AABBCCDDEEFF",
                "size_bytes": 70000000,
                "type": "base",
            }
        ],
        "lua_script_url": "https://example.com/1091500.lua",
    }

    app_info = client._parse_json_app_info(sample_json)
    assert app_info.app_id == 1091500
    assert app_info.name == "Cyberpunk 2077"
    assert len(app_info.depots) == 1
    assert app_info.depots[0].depot_id == 1091501
    assert app_info.depots[0].manifest_id == "8472918392817281920"


def test_parse_depotbox_search_html():
    client = DepotboxClient()
    sample_html = """
    <div class="search-result" data-appid="730">
        <a class="app-link" href="/app/730">Counter-Strike 2</a>
        <img src="https://example.com/cs2.jpg" />
    </div>
    <div class="search-result" data-appid="500">
        <a class="app-link" href="/app/500">Portal 2</a>
        <img src="https://example.com/portal2.jpg" />
    </div>
    """

    results = client._parse_depotbox_search_html(sample_html)
    assert len(results) == 2
    assert results[0].app_id == 730
    assert results[0].name == "Counter-Strike 2"
    assert results[1].app_id == 500
    assert results[1].name == "Portal 2"


def test_retry_mechanism_on_failure():
    mock_session = MagicMock()
    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 500
    mock_session.request.return_value = mock_resp_fail

    client = DepotboxClient(session=mock_session)
    res = client._request_with_retry("GET", "https://example.com/fail", max_retries=2)
    assert res is None
    assert mock_session.request.call_count == 2
