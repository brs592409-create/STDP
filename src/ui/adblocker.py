"""Built-in high-performance AdBlocker for PyQt6 WebEngine using URL Interception and DOM CSS/JS injection."""

from __future__ import annotations

import re
from typing import Set
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)

from src.core.logger import get_logger

logger = get_logger("ui.adblocker")


class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    """Network-level ad and tracking request interceptor."""

    # Fast domain hash set for instant O(1) matching
    BLOCKED_DOMAINS: Set[str] = {
        # Major Ad Networks & Trackers
        "doubleclick.net",
        "googlesyndication.com",
        "google-analytics.com",
        "googleadservices.com",
        "adnxs.com",
        "adservice.google.com",
        "pagead2.googlesyndication.com",
        "yandex.ru/ads",
        "an.yandex.ru",
        "mc.yandex.ru",
        # Popunder / Redirect / Malicious Ad Networks
        "popcash.net",
        "popads.net",
        "propellerads.com",
        "adsterra.com",
        "monetag.com",
        "exoclick.com",
        "clickadu.com",
        "hilltopads.net",
        "admob.com",
        "taboola.com",
        "outbrain.com",
        "mgid.com",
        "zeroredirect1.com",
        "trafficjunky.com",
        "clarium.global",
        "bidgear.com",
        "richaudience.com",
        "adtrue.com",
        "ad-maven.com",
        "admaven.com",
        "adfox.ru",
        "amung.us",
        "onclkds.com",
        "realsrv.com",
        "vungle.com",
        "inmobi.com",
        "applovin.com",
        "eflewandatnig.org",
        "eflewandatnig",
        "bet365.com",
        "1xbet.com",
        "mostbet.com",
        "vulkan",
        "redirect",
        "shortener",
    }

    # Keyword patterns in URLs
    BLOCKED_PATTERNS = [
        r"/ads?[/_.\?]",
        r"banner",
        r"popunder",
        r"adserver",
        r"trafficjunky",
        r"adsystem",
        r"adsterra",
        r"monetag",
        r"clickunder",
        r"advert",
        r"tracking",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._compiled_regex = [re.compile(p, re.IGNORECASE) for p in self.BLOCKED_PATTERNS]

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        """Inspect and block matching ad / tracker requests before transmission."""
        url = info.requestUrl()
        host = url.host().lower()
        url_str = url.toString().lower()

        # 1. Fast Domain Check
        for blocked in self.BLOCKED_DOMAINS:
            if host == blocked or host.endswith("." + blocked):
                info.block(True)
                return

        # 2. Pattern Check for Third-party Ads (Exclude main domain assets)
        if "online-fix.me" not in host and "depotbox.org" not in host and "pixeldrain.com" not in host:
            for regex in self._compiled_regex:
                if regex.search(url_str):
                    info.block(True)
                    return


# CSS rules to hide remaining in-page banners, popups, floating trading ads, and promo cards
ADBLOCK_CSS = """
/* Hide standard ad containers & iframes */
iframe[src*="ad"],
iframe[id*="ad"],
iframe[class*="ad"],
div[class*="banner"],
div[id*="banner"],
div[class*="advert"],
div[id*="advert"],
div[class*="popup-adv"],
div[id*="popup-adv"],
.ad-banner,
.adsbygoogle,
.yandex-adaptive,
.ya-distr,
.ya-share2,

/* Specific floating widgets (OperaGX, Crypto/Trading brokers, sticky popups) */
div[style*="position: fixed"][style*="z-index"][style*="bottom"],
div[style*="position: fixed"][style*="z-index"][style*="top: 0"],
div[class*="floating-ad"],
div[class*="sticky-ad"],
div[id*="announcementModal"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    height: 0 !important;
    width: 0 !important;
    max-height: 0 !important;
}
"""

ADBLOCK_JS = """
(function() {
    // 1. Prevent intrusive window.open popunders/redirects
    const originalOpen = window.open;
    window.open = function(url, name, specs) {
        if (!url || url === 'about:blank' || url.includes('ad') || url.includes('click') || url.includes('track') || url.includes('banner')) {
            console.log('[STDP AdBlock] Blocked popup window.open:', url);
            return null;
        }
        return originalOpen.apply(this, arguments);
    };

    // 2. Inject CSS
    function injectStyle() {
        if (document.getElementById('stdp-adblock-style')) return;
        const style = document.createElement('style');
        style.id = 'stdp-adblock-style';
        style.type = 'text/css';
        style.innerHTML = `""" + ADBLOCK_CSS.replace("\n", " ") + """`;
        (document.head || document.documentElement).appendChild(style);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectStyle);
    } else {
        injectStyle();
    }

    // 3. Periodic cleaner for dynamically injected floating banners
    setInterval(function() {
        document.querySelectorAll('div, section, aside').forEach(function(el) {
            const txt = (el.innerText || '').toLowerCase();
            const cls = (el.className || '').toString().toLowerCase();
            if (
                (txt.includes('trade with trusted') || txt.includes('operagx') || txt.includes('trading now')) &&
                (getComputedStyle(el).position === 'fixed' || getComputedStyle(el).position === 'absolute')
            ) {
                el.remove();
            }
        });

        // Only rewrite legitimate hoster links to _self (DO NOT rewrite ad popunder links!)
        const trustedHosts = ['online-fix.me', 'pixeldrain.com', 'google.com', 'drive.google', 'mega.nz', 'qiwi', 'fichier', 'gofile', 'mediafire'];
        document.querySelectorAll('a[target="_blank"]').forEach(function(a) {
            const h = (a.href || '').toLowerCase();
            if (trustedHosts.some(function(th) { return h.includes(th); })) {
                a.target = '_self';
            } else {
                // If it looks like an ad or untrusted redirect, disarm it
                if (h.includes('ad') || h.includes('click') || h.includes('pop') || h.includes('eflewandatnig') || h.includes('track')) {
                    a.removeAttribute('href');
                    a.onclick = function(e) { e.preventDefault(); e.stopPropagation(); return false; };
                }
            }
        });
    }, 1000);
})();
"""


def setup_adblocker_on_profile(profile: QWebEngineProfile) -> AdBlockInterceptor:
    """Attach the AdBlockInterceptor and user scripts to a QWebEngineProfile."""
    interceptor = AdBlockInterceptor()
    profile.setUrlRequestInterceptor(interceptor)

    script = QWebEngineScript()
    script.setName("STDP_AdBlocker_Script")
    script.setSourceCode(ADBLOCK_JS)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(True)

    profile.scripts().insert(script)
    logger.info("AdBlocker interceptor and DOM cleaner script attached to profile.")
    return interceptor
