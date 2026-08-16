"""Depotbox API client, web scraper, and Steam Store metadata provider."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup

from src.core.config import config_manager
from src.core.logger import get_logger
from src.core.models import AppInfo, DepotInfo

logger = get_logger("depotbox.client")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


class DepotboxClient:
    """Client for querying Depotbox and Steam Store APIs with automatic retries."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        cfg = config_manager.config
        self.base_url = (base_url or cfg.depotbox_api_url).rstrip("/")
        self.timeout = timeout_seconds or cfg.depotbox_timeout_seconds
        self.session = session or requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> Optional[requests.Response]:
        """Execute HTTP request with exponential backoff (1s, 2s, 4s)."""
        kwargs.setdefault("timeout", self.timeout)
        delay = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                if response.status_code == 200:
                    return response
                logger.warning(
                    f"HTTP {response.status_code} on {url} (Attempt {attempt}/{max_retries})"
                )
            except requests.RequestException as e:
                logger.warning(
                    f"Request failed for {url} on attempt {attempt}/{max_retries}: {e}"
                )

            if attempt < max_retries:
                time.sleep(delay)
                delay *= 2.0

        logger.error(f"All {max_retries} attempts failed for URL: {url}")
        return None

    def search(self, query: str) -> List[AppInfo]:
        """Search for games on Depotbox or fallback to Steam Store search."""
        query = query.strip()
        if not query:
            return []

        results: List[AppInfo] = []

        # If user searched by numeric AppID directly
        if query.isdigit():
            app_id = int(query)
            details = self.get_game_details(app_id)
            if details:
                return [details]
            # Fallback to Steam Store metadata if Depotbox has no full details
            steam_meta = self.fetch_steam_store_metadata(app_id)
            if steam_meta:
                return [steam_meta]

        # 1. Attempt searching Depotbox
        search_url = f"{self.base_url}/search"
        resp = self._request_with_retry("GET", search_url, params={"q": query})

        if resp and resp.text:
            results = self._parse_depotbox_search_html(resp.text)

        # 2. If no results or Depotbox is unavailable, query Steam Store API search
        if not results:
            results = self.search_steam_store(query)

        return results

    def _parse_depotbox_search_html(self, html: str) -> List[AppInfo]:
        """Parse HTML search results page from Depotbox."""
        results: List[AppInfo] = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            # Parse search result cards or tables
            cards = soup.select(".game-card, .search-result, .list-group-item, tr.app-row")
            for card in cards:
                app_id_attr = card.get("data-appid") or card.get("data-id")
                name_elem = card.select_one(".game-title, .title, a.app-link, td.name")
                img_elem = card.select_one("img")

                app_id: Optional[int] = None
                if app_id_attr and str(app_id_attr).isdigit():
                    app_id = int(app_id_attr)
                elif name_elem and name_elem.get("href"):
                    href = str(name_elem.get("href"))
                    parts = href.split("/")
                    for p in parts:
                        if p.isdigit():
                            app_id = int(p)
                            break

                name = name_elem.get_text(strip=True) if name_elem else "Unknown Game"
                thumb_url = img_elem.get("src") if img_elem else None

                if app_id:
                    results.append(
                        AppInfo(
                            app_id=app_id,
                            name=name,
                            thumbnail_url=str(thumb_url) if thumb_url else None,
                            header_url=f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg",
                        )
                    )
        except Exception as e:
            logger.warning(f"Error parsing Depotbox search HTML: {e}")

        return results

    def get_game_details(self, app_id: int) -> Optional[AppInfo]:
        """Fetch complete depot list, manifest links, and depot keys for an AppID."""
        url = f"{self.base_url}/api/app/{app_id}"
        resp = self._request_with_retry("GET", url)

        if resp:
            try:
                data = resp.json()
                if isinstance(data, dict):
                    return self._parse_json_app_info(data)
            except Exception:
                pass

        # Try HTML view if JSON endpoint is not available
        html_url = f"{self.base_url}/app/{app_id}"
        html_resp = self._request_with_retry("GET", html_url)
        if html_resp and html_resp.text:
            return self._parse_html_app_details(app_id, html_resp.text)

        # Fallback to Steam Store metadata
        return self.fetch_steam_store_metadata(app_id)

    def _parse_json_app_info(self, data: Dict[str, Any]) -> AppInfo:
        """Parse structured JSON dictionary into AppInfo model."""
        app_id = int(data.get("app_id") or data.get("appid") or 0)
        name = str(data.get("game_name") or data.get("name") or f"App {app_id}")
        thumb = data.get("thumbnail_url")
        header = data.get("header_url") or f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg"

        depots: List[DepotInfo] = []
        raw_depots = data.get("depots", [])
        if isinstance(raw_depots, list):
            for d in raw_depots:
                if isinstance(d, dict):
                    depot_id = int(d.get("depot_id") or d.get("id") or 0)
                    if depot_id:
                        depots.append(
                            DepotInfo(
                                depot_id=depot_id,
                                manifest_id=str(d.get("manifest_id") or "") or None,
                                depot_key=str(d.get("depot_key") or "") or None,
                                manifest_url=str(d.get("manifest_url") or "") or None,
                                size_bytes=int(d.get("size_bytes") or d.get("size") or 0),
                                depot_type=str(d.get("type") or "base"),
                                name=d.get("name"),
                            )
                        )

        return AppInfo(
            app_id=app_id,
            name=name,
            thumbnail_url=thumb,
            header_url=header,
            depots=depots,
            lua_script_url=data.get("lua_script_url"),
            lua_content=data.get("lua_content"),
        )

    def _parse_html_app_details(self, app_id: int, html: str) -> AppInfo:
        """Extract depots and keys from Depotbox game details HTML."""
        soup = BeautifulSoup(html, "html.parser")
        title_elem = soup.select_one("h1, .game-title, title")
        name = title_elem.get_text(strip=True) if title_elem else f"App {app_id}"

        depots: List[DepotInfo] = []
        rows = soup.select("table.depots-table tr, .depot-row")
        for r in rows:
            cols = r.select("td, .col")
            if len(cols) >= 2:
                depot_text = cols[0].get_text(strip=True)
                manifest_text = cols[1].get_text(strip=True)
                key_text = cols[2].get_text(strip=True) if len(cols) > 2 else None

                if depot_text.isdigit():
                    depots.append(
                        DepotInfo(
                            depot_id=int(depot_text),
                            manifest_id=manifest_text if manifest_text.isdigit() else None,
                            depot_key=key_text,
                        )
                    )

        return AppInfo(
            app_id=app_id,
            name=name,
            header_url=f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg",
            depots=depots,
        )

    def fetch_steam_store_metadata(self, app_id: int) -> Optional[AppInfo]:
        """Query official Steam Store API to retrieve verified game name and banner image."""
        url = "https://store.steampowered.com/api/appdetails"
        resp = self._request_with_retry("GET", url, params={"appids": str(app_id), "l": "english"})

        if resp:
            try:
                data = resp.json()
                app_data = data.get(str(app_id), {})
                if app_data.get("success") and "data" in app_data:
                    info = app_data["data"]
                    return AppInfo(
                        app_id=app_id,
                        name=info.get("name", f"App {app_id}"),
                        thumbnail_url=info.get("capsule_image"),
                        header_url=info.get("header_image"),
                        install_dir_name=info.get("name"),
                    )
            except Exception as e:
                logger.warning(f"Error parsing Steam Store metadata for AppID {app_id}: {e}")

        return None

    def search_steam_store(self, query: str) -> List[AppInfo]:
        """Search Steam Store via public search suggest / store endpoint."""
        url = "https://store.steampowered.com/api/storesearch"
        resp = self._request_with_retry(
            "GET",
            url,
            params={"term": query, "l": "english", "cc": "US"},
        )

        results: List[AppInfo] = []
        if resp:
            try:
                data = resp.json()
                items = data.get("items", [])
                for item in items:
                    app_id = item.get("id")
                    if app_id:
                        results.append(
                            AppInfo(
                                app_id=int(app_id),
                                name=item.get("name", f"App {app_id}"),
                                thumbnail_url=item.get("tiny_image"),
                                header_url=f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_id}/header.jpg",
                            )
                        )
            except Exception as e:
                logger.warning(f"Steam Store search error: {e}")

        return results


# Global singleton client
depotbox_client = DepotboxClient()
