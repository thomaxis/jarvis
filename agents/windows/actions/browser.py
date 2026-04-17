"""Browser control: open URLs, search."""

from __future__ import annotations

import logging
import subprocess
import webbrowser

log = logging.getLogger("jarvis.actions.browser")


def open_url(url: str) -> tuple[bool, str]:
    """Open a URL in the default browser."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    try:
        webbrowser.open(url)
        return True, f"Opened {url}"
    except Exception as e:
        return False, f"Failed to open URL: {e}"


def search_web(query: str, engine: str = "google") -> tuple[bool, str]:
    """Search the web with the given query."""
    engines = {
        "google": "https://www.google.com/search?q=",
        "duckduckgo": "https://duckduckgo.com/?q=",
        "bing": "https://www.bing.com/search?q=",
    }
    base_url = engines.get(engine.lower(), engines["google"])
    url = f"{base_url}{query.replace(' ', '+')}"
    return open_url(url)
