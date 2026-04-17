"""Spotify Web API client with OAuth PKCE authentication."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import httpx

from brain.src.logger import get_logger
from plugins.config import get_plugin_config, save_plugin_config

log = get_logger("spotify_api")

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-playback-state user-modify-playback-state user-read-currently-playing"


class SpotifyAPI:
    """Spotify Web API client."""

    def __init__(
        self,
        client_id: str = "",
        access_token: str = "",
        refresh_token: str = "",
    ) -> None:
        self._client_id = client_id
        self._access_token = access_token
        self._refresh_token = refresh_token

    async def authenticate(self) -> dict[str, str] | None:
        """Run OAuth PKCE flow. Opens browser, catches callback, returns tokens."""
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )

        params = {
            "client_id": self._client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "code_challenge_method": "S256",
            "code_challenge": code_challenge,
        }
        auth_url = f"{SPOTIFY_AUTH_URL}?{urllib.parse.urlencode(params)}"

        # Catch the callback
        auth_code = await self._open_browser_and_catch_code(auth_url)
        if not auth_code:
            return None

        # Exchange code for tokens
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(SPOTIFY_TOKEN_URL, data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": REDIRECT_URI,
                "client_id": self._client_id,
                "code_verifier": code_verifier,
            })

            if resp.status_code != 200:
                log.error("Token exchange failed: %s %s", resp.status_code, resp.text)
                return None

            data = resp.json()
            self._access_token = data["access_token"]
            self._refresh_token = data["refresh_token"]

            log.info("Spotify authenticated")
            return {
                "access_token": self._access_token,
                "refresh_token": self._refresh_token,
            }

    async def _open_browser_and_catch_code(self, auth_url: str) -> str | None:
        """Open browser for auth and run a local server to catch the redirect."""
        code_holder: dict[str, str | None] = {"code": None}

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                query = urllib.parse.urlparse(self.path).query
                params = urllib.parse.parse_qs(query)
                code_holder["code"] = params.get("code", [None])[0]

                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                html = (
                    "<html><body style='background:#0f0f1a;color:#e2e8f0;font-family:sans-serif;"
                    "display:flex;align-items:center;justify-content:center;height:100vh;margin:0'>"
                    "<div style='text-align:center'>"
                    "<h1 style='color:#6366f1'>Jarvis + Spotify Connected</h1>"
                    "<p>You can close this tab and go back to Jarvis.</p>"
                    "</div></body></html>"
                )
                self.wfile.write(html.encode())

            def log_message(self, format, *args):
                pass  # Suppress HTTP logs

        server = HTTPServer(("127.0.0.1", 8888), CallbackHandler)
        server.timeout = 120  # 2 minute timeout

        # Open browser
        webbrowser.open(auth_url)
        log.info("Opened browser for Spotify auth. Waiting for callback...")

        # Handle one request (the callback)
        def serve():
            server.handle_request()
            server.server_close()

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        thread.join(timeout=120)

        return code_holder["code"]

    async def ensure_token(self) -> None:
        """Refresh access token if needed."""
        if not self._refresh_token:
            return

        # Try a simple API call to check if token is valid
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SPOTIFY_API_BASE}/me/player",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            if resp.status_code != 401:
                return  # Token is still valid

        # Refresh
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(SPOTIFY_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
            })

            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data["access_token"]
                if "refresh_token" in data:
                    self._refresh_token = data["refresh_token"]

                # Persist new tokens
                config = get_plugin_config("spotify")
                config["access_token"] = self._access_token
                if "refresh_token" in data:
                    config["refresh_token"] = self._refresh_token
                save_plugin_config("spotify", config)

                log.info("Spotify token refreshed")
            else:
                log.error("Token refresh failed: %s", resp.text)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    async def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search for tracks."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SPOTIFY_API_BASE}/search",
                headers=self._headers(),
                params={"q": query, "type": "track", "limit": limit},
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            tracks = []
            for item in data.get("tracks", {}).get("items", []):
                tracks.append({
                    "name": item["name"],
                    "artist": ", ".join(a["name"] for a in item["artists"]),
                    "album": item["album"]["name"],
                    "uri": item["uri"],
                    "id": item["id"],
                })
            return tracks

    async def play_track(self, uri: str) -> bool:
        """Play a specific track by URI."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{SPOTIFY_API_BASE}/me/player/play",
                headers=self._headers(),
                json={"uris": [uri]},
            )
            return resp.status_code in (200, 204)

    async def resume(self) -> bool:
        """Resume current playback."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{SPOTIFY_API_BASE}/me/player/play",
                headers=self._headers(),
            )
            return resp.status_code in (200, 204)

    async def pause(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{SPOTIFY_API_BASE}/me/player/pause",
                headers=self._headers(),
            )
            return resp.status_code in (200, 204)

    async def next(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{SPOTIFY_API_BASE}/me/player/next",
                headers=self._headers(),
            )
            return resp.status_code in (200, 204)

    async def previous(self) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{SPOTIFY_API_BASE}/me/player/previous",
                headers=self._headers(),
            )
            return resp.status_code in (200, 204)

    async def set_volume(self, percent: int) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{SPOTIFY_API_BASE}/me/player/volume",
                headers=self._headers(),
                params={"volume_percent": percent},
            )
            return resp.status_code in (200, 204)

    async def get_current(self) -> dict | None:
        """Get currently playing track info."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SPOTIFY_API_BASE}/me/player/currently-playing",
                headers=self._headers(),
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            item = data.get("item")
            if not item:
                return None

            return {
                "name": item["name"],
                "artist": ", ".join(a["name"] for a in item["artists"]),
                "album": item["album"]["name"],
                "uri": item["uri"],
                "is_playing": data.get("is_playing", False),
            }
