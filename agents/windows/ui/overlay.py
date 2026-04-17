"""Optional floating overlay for desktop -- shows Jarvis responses and status."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

log = logging.getLogger("jarvis.overlay")


class DesktopOverlay:
    """Transparent floating overlay window for Jarvis responses.

    Uses tkinter for cross-platform compatibility. Shows a semi-transparent
    window in the corner that displays the last response.
    """

    def __init__(
        self,
        position: str = "bottom-right",
        opacity: float = 0.85,
        width: int = 400,
        height: int = 150,
    ) -> None:
        self._position = position
        self._opacity = opacity
        self._width = width
        self._height = height
        self._root: Any = None
        self._label: Any = None
        self._enabled = False
        self._thread: threading.Thread | None = None

    def initialize(self) -> bool:
        try:
            import tkinter
            self._enabled = True
            log.info("Overlay initialized")
            return True
        except ImportError:
            log.warning("tkinter not available. Overlay disabled.")
            return False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def show(self, text: str, duration: int = 5) -> None:
        """Show a message in the overlay for `duration` seconds."""
        if not self._enabled:
            return

        if self._thread and self._thread.is_alive():
            # Update existing overlay
            if self._label:
                try:
                    self._label.config(text=text)
                    return
                except Exception:
                    pass

        self._thread = threading.Thread(
            target=self._show_window, args=(text, duration), daemon=True
        )
        self._thread.start()

    def _show_window(self, text: str, duration: int) -> None:
        try:
            import tkinter as tk

            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", self._opacity)

            # Position
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()

            positions = {
                "bottom-right": (screen_w - self._width - 20, screen_h - self._height - 60),
                "bottom-left": (20, screen_h - self._height - 60),
                "top-right": (screen_w - self._width - 20, 40),
                "top-left": (20, 40),
            }
            x, y = positions.get(self._position, positions["bottom-right"])
            root.geometry(f"{self._width}x{self._height}+{x}+{y}")

            # Style
            root.configure(bg="#1a1a2e")

            frame = tk.Frame(root, bg="#1a1a2e", padx=15, pady=10)
            frame.pack(fill=tk.BOTH, expand=True)

            header = tk.Label(
                frame, text="Jarvis", font=("Segoe UI", 10, "bold"),
                bg="#1a1a2e", fg="#6366f1", anchor="w",
            )
            header.pack(fill=tk.X)

            self._label = tk.Label(
                frame, text=text, font=("Segoe UI", 11),
                bg="#1a1a2e", fg="#e0e0e0", anchor="nw",
                wraplength=self._width - 40, justify="left",
            )
            self._label.pack(fill=tk.BOTH, expand=True)

            self._root = root

            # Auto-close after duration
            root.after(duration * 1000, root.destroy)
            root.mainloop()
        except Exception as e:
            log.error("Overlay failed: %s", e)

    def hide(self) -> None:
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
