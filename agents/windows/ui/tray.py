"""Windows system tray icon with connection status and menu."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

log = logging.getLogger("jarvis.tray")


class SystemTray:
    """System tray icon showing Jarvis connection status."""

    def __init__(
        self,
        on_text_mode: Callable | None = None,
        on_quit: Callable | None = None,
    ) -> None:
        self._icon: Any = None
        self._on_text_mode = on_text_mode
        self._on_quit = on_quit
        self._connected = False
        self._enabled = False

    def initialize(self) -> bool:
        try:
            import pystray
            from PIL import Image
            self._pystray = pystray
            self._Image = Image
            self._enabled = True
            log.info("System tray initialized")
            return True
        except ImportError:
            log.warning("pystray or Pillow not installed. Tray disabled.")
            return False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        if self._icon:
            self._icon.icon = self._create_icon(connected)

    def run(self) -> None:
        """Run the system tray in a background thread."""
        if not self._enabled:
            return

        thread = threading.Thread(target=self._run_tray, daemon=True)
        thread.start()

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()

    def _run_tray(self) -> None:
        menu = self._pystray.Menu(
            self._pystray.MenuItem("Jarvis OS", None, enabled=False),
            self._pystray.Menu.SEPARATOR,
            self._pystray.MenuItem(
                lambda _: f"Status: {'Connected' if self._connected else 'Disconnected'}",
                None,
                enabled=False,
            ),
            self._pystray.Menu.SEPARATOR,
            self._pystray.MenuItem("Text Mode", self._handle_text_mode),
            self._pystray.MenuItem("Quit", self._handle_quit),
        )

        self._icon = self._pystray.Icon(
            "jarvis",
            self._create_icon(self._connected),
            "Jarvis OS",
            menu,
        )
        self._icon.run()

    def _create_icon(self, connected: bool) -> Any:
        """Create a simple colored circle icon."""
        size = 64
        img = self._Image.new("RGBA", (size, size), (0, 0, 0, 0))

        # Draw a circle
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        color = (76, 175, 80, 255) if connected else (244, 67, 54, 255)  # Green or Red
        draw.ellipse([4, 4, size - 4, size - 4], fill=color)

        # Draw "J" in the center
        try:
            draw.text((size // 2 - 8, size // 2 - 12), "J", fill=(255, 255, 255, 255))
        except Exception:
            pass

        return img

    def _handle_text_mode(self, icon: Any, item: Any) -> None:
        if self._on_text_mode:
            self._on_text_mode()

    def _handle_quit(self, icon: Any, item: Any) -> None:
        icon.stop()
        if self._on_quit:
            self._on_quit()
