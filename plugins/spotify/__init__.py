"""Spotify plugin -- real playback control via Spotify Web API.

Setup flow: Jarvis detects the plugin is unconfigured, asks the user for their
Spotify Client ID, opens the browser for OAuth, and saves the tokens automatically.
"""

from __future__ import annotations

import logging
from typing import Any

from plugins.base import JarvisPlugin
from plugins.config import get_plugin_config, is_plugin_configured, save_plugin_config
from plugins.spotify.api import SpotifyAPI

log = logging.getLogger("jarvis.plugins.spotify")


class SpotifyPlugin(JarvisPlugin):
    @property
    def name(self) -> str:
        return "spotify"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Control Spotify playback (play, pause, skip, search, volume)"

    async def initialize(self, brain: Any) -> bool:
        config = get_plugin_config("spotify")
        if config.get("configured") and config.get("refresh_token"):
            self._api = SpotifyAPI(
                client_id=config["client_id"],
                refresh_token=config["refresh_token"],
                access_token=config.get("access_token", ""),
            )
            log.info("Spotify plugin loaded (authenticated)")
        else:
            self._api = None
            log.info("Spotify plugin loaded (not configured -- will prompt user)")
        return True

    def is_configured(self) -> bool:
        return self._api is not None and is_plugin_configured("spotify")

    def get_setup_instructions(self) -> str:
        return (
            "To set up Spotify, I need your Spotify Client ID. Here's how to get one:\n"
            "1. Go to https://developer.spotify.com/dashboard\n"
            "2. Click 'Create App'\n"
            "3. Set the redirect URI to: http://127.0.0.1:8888/callback\n"
            "4. Copy the Client ID and tell it to me.\n\n"
            "Just say: 'My Spotify Client ID is <your_id>'"
        )

    async def setup(self, client_id: str) -> tuple[bool, str]:
        """Run OAuth PKCE flow to authenticate with Spotify."""
        try:
            api = SpotifyAPI(client_id=client_id)
            tokens = await api.authenticate()

            if not tokens:
                return False, "Authentication failed. Make sure you approved the request in your browser."

            save_plugin_config("spotify", {
                "configured": True,
                "client_id": client_id,
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            })

            self._api = api
            return True, "Spotify connected. Try saying 'play some music' or 'play <song name>'."

        except Exception as e:
            log.error("Spotify setup failed: %s", e)
            return False, f"Setup failed: {e}"

    def get_actions(self) -> dict[str, Any]:
        return {
            "spotify_play": self.play,
            "spotify_pause": self.pause,
            "spotify_next": self.next_track,
            "spotify_previous": self.previous_track,
            "spotify_volume": self.set_volume,
            "spotify_current": self.now_playing,
            "spotify_search": self.search,
            "spotify_setup": self.setup,
        }

    def get_intents(self) -> list[tuple[str, str]]:
        return [
            (r"\bplay\s+(.+?)(?:\s+on\s+spotify)?\s*$", "spotify_play"),
            (r"\bpause\s*(?:the\s*)?(?:music|song|spotify)?\s*$", "spotify_pause"),
            (r"\b(?:next|skip)\s*(?:song|track)?\s*$", "spotify_next"),
            (r"\bprevious\s*(?:song|track)?\s*$", "spotify_previous"),
            (r"\bwhat(?:'s| is) playing\b", "spotify_current"),
            (r"\bnow playing\b", "spotify_current"),
        ]

    async def play(self, target: str = "", **kwargs: Any) -> tuple[bool, str]:
        if not self._api:
            return False, self.get_setup_instructions()

        await self._api.ensure_token()

        if not target:
            ok = await self._api.resume()
            return (True, "Resumed playback.") if ok else (False, "No active Spotify device found. Open Spotify first.")

        # Search and play
        tracks = await self._api.search(target, limit=1)
        if not tracks:
            return False, f"No results for '{target}' on Spotify."

        track = tracks[0]
        ok = await self._api.play_track(track["uri"])
        if ok:
            return True, f"Playing: {track['name']} by {track['artist']}"
        return False, "Failed to play. Make sure Spotify is open on a device."

    async def pause(self, **kwargs: Any) -> tuple[bool, str]:
        if not self._api:
            return False, self.get_setup_instructions()
        await self._api.ensure_token()
        ok = await self._api.pause()
        return (True, "Paused.") if ok else (False, "Nothing is playing.")

    async def next_track(self, **kwargs: Any) -> tuple[bool, str]:
        if not self._api:
            return False, self.get_setup_instructions()
        await self._api.ensure_token()
        ok = await self._api.next()
        return (True, "Skipped to next track.") if ok else (False, "Failed to skip.")

    async def previous_track(self, **kwargs: Any) -> tuple[bool, str]:
        if not self._api:
            return False, self.get_setup_instructions()
        await self._api.ensure_token()
        ok = await self._api.previous()
        return (True, "Previous track.") if ok else (False, "Failed to go back.")

    async def set_volume(self, target: str = "50", **kwargs: Any) -> tuple[bool, str]:
        if not self._api:
            return False, self.get_setup_instructions()
        await self._api.ensure_token()
        try:
            vol = max(0, min(100, int(target)))
        except ValueError:
            return False, "Volume must be a number 0-100."
        ok = await self._api.set_volume(vol)
        return (True, f"Spotify volume set to {vol}%.") if ok else (False, "Failed to set volume.")

    async def now_playing(self, **kwargs: Any) -> tuple[bool, str]:
        if not self._api:
            return False, self.get_setup_instructions()
        await self._api.ensure_token()
        info = await self._api.get_current()
        if info:
            return True, f"Now playing: {info['name']} by {info['artist']} ({info['album']})"
        return False, "Nothing is currently playing."

    async def search(self, query: str = "", **kwargs: Any) -> tuple[bool, str]:
        if not self._api:
            return False, self.get_setup_instructions()
        await self._api.ensure_token()
        tracks = await self._api.search(query, limit=5)
        if not tracks:
            return False, f"No results for '{query}'."
        lines = [f"{i+1}. {t['name']} -- {t['artist']}" for i, t in enumerate(tracks)]
        return True, "Found:\n" + "\n".join(lines)
