"""Jarvis Windows GUI Application.

Modern desktop app with system tray, chat interface, and voice.
Built with customtkinter for a polished look.

Usage: python agents/windows/app.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

import customtkinter as ctk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis.app")

# --- Theme ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Palette
BG_BASE = "#0b0b14"
BG_SIDEBAR = "#10101e"
BG_CHAT = "#0e0e1a"
BG_INPUT_BAR = "#131324"
BG_INPUT_FIELD = "#1a1a30"
BG_USER_BUBBLE = "#1e1e3a"
BG_JARVIS_BUBBLE = "#16162e"
BORDER_SUBTLE = "#1f1f3a"
ACCENT = "#6366f1"
ACCENT_LIGHT = "#818cf8"
ACCENT_DIM = "#4f46e5"
TEXT_WHITE = "#f1f5f9"
TEXT_LIGHT = "#cbd5e1"
TEXT_MID = "#94a3b8"
TEXT_DIM = "#475569"
GREEN_DOT = "#34d399"
RED_DOT = "#f87171"
MIC_PULSE = "#ef4444"
MIC_IDLE_CLR = "#6366f1"


# --- Voice Engine (unchanged logic, cleaned up) ---

class VoiceEngine:
    def __init__(self) -> None:
        self._recognizer = None
        self._tts_engine = None
        self._stt_ready = False
        self._tts_ready = False
        self._tts_lock = threading.Lock()

    def initialize(self) -> dict[str, bool]:
        status = {"stt": False, "tts": False}
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 1.0
            with sr.Microphone() as _:
                pass
            self._stt_ready = True
            status["stt"] = True
            log.info("STT ready")
        except Exception as e:
            log.warning("STT disabled: %s", e)

        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 175)
            voices = self._tts_engine.getProperty("voices")
            for v in voices:
                if "david" in v.name.lower() or "mark" in v.name.lower():
                    self._tts_engine.setProperty("voice", v.id)
                    break
            self._tts_ready = True
            status["tts"] = True
            log.info("TTS ready")
        except Exception as e:
            log.warning("TTS disabled: %s", e)
        return status

    @property
    def stt_ready(self) -> bool:
        return self._stt_ready

    @property
    def tts_ready(self) -> bool:
        return self._tts_ready

    def listen(self, timeout: int = 8, phrase_limit: int = 15) -> str:
        if not self._stt_ready:
            return ""
        import speech_recognition as sr
        try:
            with sr.Microphone() as src:
                self._recognizer.adjust_for_ambient_noise(src, duration=0.3)
                audio = self._recognizer.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
            return self._recognizer.recognize_google(audio)
        except Exception:
            return ""

    def speak(self, text: str) -> None:
        if not self._tts_ready:
            return
        def _do():
            with self._tts_lock:
                try:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                except Exception:
                    pass
        threading.Thread(target=_do, daemon=True).start()


# --- Main App ---

class JarvisApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self._ws = None
        self._connected = False
        self._running = True
        self._listening = False
        self._loop: asyncio.AbstractEventLoop | None = None

        # Config
        self._device_id = os.environ.get("JARVIS_DEVICE_ID", "windows-gui")
        self._brain_ws = os.environ.get("JARVIS_BRAIN_WS", "ws://localhost:8400/ws")
        self._token = os.environ.get("JARVIS_AGENT_TOKEN", "")

        # Voice
        self._voice = VoiceEngine()
        self._voice_status = self._voice.initialize()

        self._build_ui()

        # Background threads
        threading.Thread(target=self._run_async_loop, daemon=True).start()
        threading.Thread(target=self._run_tray, daemon=True).start()

    def _build_ui(self) -> None:
        self.title("Jarvis")
        self.geometry("480x720")
        self.minsize(400, 550)
        self.configure(fg_color=BG_BASE)
        self.protocol("WM_DELETE_WINDOW", self._hide_window)

        # ---- Header ----
        header = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Left: logo + status
        left = ctk.CTkFrame(header, fg_color="transparent")
        left.pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            left, text="J", font=ctk.CTkFont("Segoe UI", 20, "bold"),
            text_color=ACCENT, width=32, height=32,
            fg_color=ACCENT_DIM, corner_radius=8,
        ).pack(side="left")

        ctk.CTkLabel(
            left, text="  JARVIS", font=ctk.CTkFont("Segoe UI", 16, "bold"),
            text_color=TEXT_WHITE,
        ).pack(side="left")

        self._status_label = ctk.CTkLabel(
            left, text="  Connecting...", font=ctk.CTkFont("Segoe UI", 11),
            text_color=TEXT_DIM,
        )
        self._status_label.pack(side="left", padx=(4, 0))

        # Right: voice badge
        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right", padx=20, pady=12)

        mic_text = "Voice ON" if self._voice_status["stt"] else "Voice OFF"
        mic_color = GREEN_DOT if self._voice_status["stt"] else RED_DOT
        self._voice_badge = ctk.CTkLabel(
            right, text=f"  {mic_text}",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=mic_color,
        )
        self._voice_badge.pack(side="right")

        # Divider
        ctk.CTkFrame(self, fg_color=BORDER_SUBTLE, height=1, corner_radius=0).pack(fill="x")

        # ---- Chat Area ----
        self._chat_scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_CHAT, corner_radius=0,
            scrollbar_button_color=BG_SIDEBAR,
            scrollbar_button_hover_color=ACCENT_DIM,
        )
        self._chat_scroll.pack(fill="both", expand=True, padx=0, pady=0)

        # Welcome
        self._add_system_msg("Welcome to Jarvis OS")
        self._add_system_msg("Connecting to brain...")

        # Divider
        ctk.CTkFrame(self, fg_color=BORDER_SUBTLE, height=1, corner_radius=0).pack(fill="x")

        # ---- Input Bar ----
        input_bar = ctk.CTkFrame(self, fg_color=BG_INPUT_BAR, corner_radius=0, height=70)
        input_bar.pack(fill="x")
        input_bar.pack_propagate(False)

        input_row = ctk.CTkFrame(input_bar, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=14)

        # Mic button
        self._mic_btn = ctk.CTkButton(
            input_row, text="\U0001F3A4", width=42, height=42,
            font=ctk.CTkFont(size=18),
            fg_color=BG_INPUT_FIELD, hover_color=ACCENT_DIM,
            corner_radius=21, border_width=0,
            command=self._on_mic_click,
        )
        if self._voice_status["stt"]:
            self._mic_btn.pack(side="left", padx=(0, 10))

        # Text entry
        self._input_entry = ctk.CTkEntry(
            input_row, placeholder_text="Message Jarvis...",
            font=ctk.CTkFont("Segoe UI", 13),
            fg_color=BG_INPUT_FIELD, border_color=BORDER_SUBTLE,
            text_color=TEXT_WHITE, placeholder_text_color=TEXT_DIM,
            corner_radius=22, height=42, border_width=1,
        )
        self._input_entry.pack(side="left", fill="x", expand=True)
        self._input_entry.bind("<Return>", self._on_send)

        # Send button
        self._send_btn = ctk.CTkButton(
            input_row, text="\u27A4", width=42, height=42,
            font=ctk.CTkFont(size=16),
            fg_color=ACCENT, hover_color=ACCENT_LIGHT,
            corner_radius=21, border_width=0,
            command=self._on_send,
        )
        self._send_btn.pack(side="right", padx=(10, 0))

        # Keyboard shortcut
        self.bind("<Control-space>", lambda e: self._on_mic_click())

        self._input_entry.focus_set()

    # ---- Chat messages ----

    def _add_message(self, role: str, text: str) -> None:
        is_user = role == "user"
        bubble_bg = BG_USER_BUBBLE if is_user else BG_JARVIS_BUBBLE
        name = "You" if is_user else "Jarvis"
        name_color = TEXT_MID if is_user else ACCENT_LIGHT
        time_str = datetime.now().strftime("%H:%M")

        # Container
        container = ctk.CTkFrame(self._chat_scroll, fg_color="transparent")
        container.pack(fill="x", padx=16, pady=(6, 2))

        # Bubble
        bubble = ctk.CTkFrame(container, fg_color=bubble_bg, corner_radius=16, border_width=1, border_color=BORDER_SUBTLE)
        bubble.pack(fill="x")

        inner = ctk.CTkFrame(bubble, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        # Header row
        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x")

        ctk.CTkLabel(
            hdr, text=name, font=ctk.CTkFont("Segoe UI", 11, "bold"),
            text_color=name_color,
        ).pack(side="left")

        ctk.CTkLabel(
            hdr, text=time_str, font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_DIM,
        ).pack(side="right")

        # Body
        ctk.CTkLabel(
            inner, text=text, font=ctk.CTkFont("Segoe UI", 12),
            text_color=TEXT_LIGHT, wraplength=380,
            justify="left", anchor="nw",
        ).pack(fill="x", pady=(6, 0))

        self._scroll_to_bottom()

    def _add_system_msg(self, text: str) -> None:
        container = ctk.CTkFrame(self._chat_scroll, fg_color="transparent")
        container.pack(fill="x", padx=16, pady=(8, 2))

        ctk.CTkLabel(
            container, text=text,
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TEXT_DIM,
        ).pack(anchor="center")

        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        self.update_idletasks()
        try:
            self._chat_scroll._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def _update_status(self, connected: bool) -> None:
        self._connected = connected
        if connected:
            self._status_label.configure(text="  Connected", text_color=GREEN_DOT)
        else:
            self._status_label.configure(text="  Disconnected", text_color=RED_DOT)

    # ---- Input ----

    def _on_send(self, event: Any = None) -> None:
        text = self._input_entry.get().strip()
        if not text:
            return
        self._input_entry.delete(0, "end")
        self._send_text(text)

    def _send_text(self, text: str) -> None:
        self._add_message("user", text)
        if self._loop and self._connected:
            asyncio.run_coroutine_threadsafe(self._ws_send(text), self._loop)
        elif not self._connected:
            self._add_system_msg("Not connected to brain.")

    # ---- Voice ----

    def _on_mic_click(self) -> None:
        if self._listening or not self._voice.stt_ready:
            return
        self._listening = True
        self._mic_btn.configure(fg_color=MIC_PULSE, text="\U0001F534")
        self._add_system_msg("Listening... speak now")
        threading.Thread(target=self._do_listen, daemon=True).start()

    def _do_listen(self) -> None:
        text = self._voice.listen(timeout=8, phrase_limit=15)
        self._listening = False
        self.after(0, self._mic_btn.configure, {"fg_color": BG_INPUT_FIELD, "text": "\U0001F3A4"})
        if text:
            self.after(0, self._send_text, text)
        else:
            self.after(0, self._add_system_msg, "Didn't catch that. Try again.")

    # ---- WebSocket ----

    def _run_async_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())

    async def _connect_loop(self) -> None:
        import websockets
        reconnect_delay = 1.0
        while self._running:
            try:
                headers = {}
                if self._token:
                    headers["Authorization"] = f"Bearer {self._token}"

                async with websockets.connect(self._brain_ws, additional_headers=headers) as ws:
                    self._ws = ws
                    await ws.send(json.dumps({
                        "event": "agent_connect",
                        "device_id": self._device_id,
                        "platform": "windows",
                        "capabilities": ["os_control", "apps", "files", "browser", "terminal", "clipboard", "system", "voice"],
                    }))
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get("event") == "connected":
                        self.after(0, self._update_status, True)
                        self.after(0, self._add_system_msg, "Brain connected. Ready.")
                        reconnect_delay = 1.0

                    async for raw in ws:
                        msg = json.loads(raw)
                        await self._handle_ws_msg(msg)

            except Exception as e:
                self._ws = None
                self.after(0, self._update_status, False)
                log.warning("Connection lost: %s. Retry in %.0fs", e, reconnect_delay)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30.0)

    async def _ws_send(self, text: str) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps({
                    "event": "user_input", "device_id": self._device_id, "text": text,
                }))
            except Exception as e:
                self.after(0, self._add_system_msg, f"Send failed: {e}")

    async def _handle_ws_msg(self, msg: dict) -> None:
        event = msg.get("event", "")
        if event == "response":
            text = msg.get("text", "")
            if text:
                self.after(0, self._add_message, "jarvis", text)
                if msg.get("tts", False) and self._voice.tts_ready:
                    self._voice.speak(text)
            for act in msg.get("actions", []):
                await self._exec_action(act)
        elif event == "notification":
            self.after(0, self._add_system_msg, msg.get("message", ""))
        elif event == "pending_task":
            self.after(0, self._add_system_msg, f"Pending: {msg.get('task', {}).get('description', '')}")

    async def _exec_action(self, action: dict) -> None:
        from agents.windows.actions import apps, browser, clipboard, files, system, terminal
        t = action.get("type", "")
        target = action.get("target", "")
        params = action.get("params", {})
        ok, detail = False, "Unknown"

        if t == "open_app": ok, detail = apps.open_app(target)
        elif t == "close_app": ok, detail = apps.close_app(target)
        elif t == "open_url": ok, detail = browser.open_url(target)
        elif t == "search": ok, detail = browser.search_web(target)
        elif t == "volume": ok, detail = system.set_volume(target)
        elif t == "system_power" and target == "lock": ok, detail = system.lock_screen()
        elif t == "terminal": ok, detail = terminal.run_command(target)
        elif t == "clipboard" and params.get("operation") == "write": ok, detail = clipboard.write_clipboard(target)

        self.after(0, self._add_system_msg, f"{'Done' if ok else 'Failed'}: {t} {target}")

    # ---- Tray ----

    def _run_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw, ImageFont

            def make_icon():
                sz = 64
                img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
                d = ImageDraw.Draw(img)
                d.rounded_rectangle([2, 2, sz-2, sz-2], radius=14, fill=(99, 102, 241, 255))
                try:
                    fnt = ImageFont.truetype("segoeuib.ttf", 32)
                    d.text((sz//2, sz//2), "J", fill=(255, 255, 255, 255), font=fnt, anchor="mm")
                except Exception:
                    d.text((20, 14), "J", fill=(255, 255, 255, 255))
                return img

            def show(icon, item):
                self.after(0, self._show_window)

            def quit_app(icon, item):
                self._running = False
                icon.stop()
                self.after(0, self.destroy)

            menu = pystray.Menu(
                pystray.MenuItem("Show Jarvis", show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", quit_app),
            )
            pystray.Icon("jarvis", make_icon(), "Jarvis OS", menu).run()
        except ImportError:
            log.warning("pystray/Pillow not installed")

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self._input_entry.focus_set()

    def _hide_window(self) -> None:
        self.withdraw()


def main() -> None:
    app = JarvisApp()
    app.mainloop()


if __name__ == "__main__":
    main()
