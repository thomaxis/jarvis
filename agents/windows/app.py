"""Jarvis Windows GUI Application.

A persistent desktop app with system tray icon, chat window, and voice support.
Connects to the brain via WebSocket and executes actions locally.

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis.app")

# --- Colors ---
BG_DARK = "#0f0f1a"
BG_PANEL = "#161625"
BG_INPUT = "#1e1e32"
BG_MSG_USER = "#2a2a4a"
BG_MSG_JARVIS = "#1a1a30"
ACCENT = "#6366f1"
ACCENT_HOVER = "#818cf8"
TEXT_PRIMARY = "#e2e8f0"
TEXT_SECONDARY = "#94a3b8"
TEXT_DIM = "#64748b"
GREEN = "#22c55e"
RED = "#ef4444"
YELLOW = "#eab308"
MIC_ACTIVE = "#ef4444"
MIC_IDLE = "#6366f1"


# --- Voice Engine ---

class VoiceEngine:
    """Handles STT (speech recognition) and TTS (text-to-speech)."""

    def __init__(self) -> None:
        self._recognizer = None
        self._tts_engine = None
        self._stt_ready = False
        self._tts_ready = False
        self._tts_lock = threading.Lock()

    def initialize(self) -> dict[str, bool]:
        """Initialize voice components. Returns status of each."""
        status = {"stt": False, "tts": False}

        # STT via SpeechRecognition
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 1.0
            # Test mic access
            with sr.Microphone() as _:
                pass
            self._stt_ready = True
            status["stt"] = True
            log.info("STT ready (SpeechRecognition + Microphone)")
        except ImportError:
            log.warning("SpeechRecognition not installed. STT disabled.")
        except OSError as e:
            log.warning("No microphone found: %s. STT disabled.", e)
        except Exception as e:
            log.warning("STT init failed: %s", e)

        # TTS via pyttsx3
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 175)
            voices = self._tts_engine.getProperty("voices")
            # Pick a natural-sounding voice if available
            for voice in voices:
                if "david" in voice.name.lower() or "mark" in voice.name.lower():
                    self._tts_engine.setProperty("voice", voice.id)
                    break
            self._tts_ready = True
            status["tts"] = True
            log.info("TTS ready (pyttsx3)")
        except Exception as e:
            log.warning("TTS init failed: %s. TTS disabled.", e)

        return status

    @property
    def stt_ready(self) -> bool:
        return self._stt_ready

    @property
    def tts_ready(self) -> bool:
        return self._tts_ready

    def listen(self, timeout: int = 8, phrase_limit: int = 15) -> str:
        """Record from mic and transcribe. Blocks until done. Returns text or empty string."""
        if not self._stt_ready or not self._recognizer:
            return ""

        import speech_recognition as sr

        try:
            with sr.Microphone() as source:
                log.info("Listening...")
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

            log.info("Transcribing...")
            # Use Google's free speech API (no key needed)
            text = self._recognizer.recognize_google(audio)
            log.info("Heard: %s", text)
            return text

        except Exception as e:
            log.warning("Listen failed: %s", type(e).__name__)
            return ""

    def speak(self, text: str) -> None:
        """Speak text via TTS. Runs in a thread to avoid blocking."""
        if not self._tts_ready or not self._tts_engine:
            return

        def _do_speak():
            with self._tts_lock:
                try:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                except Exception as e:
                    log.warning("TTS speak failed: %s", e)

        threading.Thread(target=_do_speak, daemon=True).start()


# --- Main App ---

class JarvisApp:
    """Main Jarvis Windows application with GUI, voice, and brain connection."""

    def __init__(self) -> None:
        self._ws = None
        self._connected = False
        self._running = True
        self._listening = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._messages: list[dict] = []

        # Config
        self._device_id = os.environ.get("JARVIS_DEVICE_ID", "windows-gui")
        self._brain_ws = os.environ.get("JARVIS_BRAIN_WS", "ws://localhost:8400/ws")
        self._token = os.environ.get("JARVIS_AGENT_TOKEN", "")

        # Voice
        self._voice = VoiceEngine()
        self._voice_status = self._voice.initialize()

        # Build GUI
        self._root = tk.Tk()
        self._root.withdraw()
        self._build_window()

        # Start async loop in background thread
        self._async_thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._async_thread.start()

        # System tray
        self._tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        self._tray_thread.start()

    def _build_window(self) -> None:
        """Build the chat window."""
        self._root.title("Jarvis")
        self._root.geometry("440x680")
        self._root.minsize(380, 520)
        self._root.configure(bg=BG_DARK)
        self._root.protocol("WM_DELETE_WINDOW", self._hide_window)
        self._root.overrideredirect(False)

        try:
            self._root.iconbitmap(default="")
        except Exception:
            pass

        # --- Title bar ---
        title_bar = tk.Frame(self._root, bg=BG_PANEL, height=50)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)

        title_left = tk.Frame(title_bar, bg=BG_PANEL)
        title_left.pack(side=tk.LEFT, padx=15, pady=8)

        tk.Label(
            title_left, text="JARVIS", font=("Segoe UI", 13, "bold"),
            bg=BG_PANEL, fg=ACCENT,
        ).pack(side=tk.LEFT)

        self._status_dot = tk.Label(
            title_left, text="\u25CF", font=("Segoe UI", 8),
            bg=BG_PANEL, fg=RED,
        )
        self._status_dot.pack(side=tk.LEFT, padx=(8, 0))

        self._status_label = tk.Label(
            title_left, text="Connecting...", font=("Segoe UI", 9),
            bg=BG_PANEL, fg=TEXT_DIM,
        )
        self._status_label.pack(side=tk.LEFT, padx=(4, 0))

        # Voice status on right
        title_right = tk.Frame(title_bar, bg=BG_PANEL)
        title_right.pack(side=tk.RIGHT, padx=15, pady=8)

        voice_indicator = "\U0001F3A4" if self._voice_status["stt"] else "\U0001F507"
        voice_tip = "Voice ready" if self._voice_status["stt"] else "No mic"
        self._voice_status_label = tk.Label(
            title_right, text=f"{voice_indicator} {voice_tip}",
            font=("Segoe UI", 9), bg=BG_PANEL, fg=TEXT_DIM,
        )
        self._voice_status_label.pack(side=tk.RIGHT)

        # --- Chat area ---
        chat_container = tk.Frame(self._root, bg=BG_DARK)
        chat_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self._chat_canvas = tk.Canvas(
            chat_container, bg=BG_DARK, highlightthickness=0, bd=0,
        )
        self._chat_scrollbar = tk.Scrollbar(
            chat_container, orient=tk.VERTICAL, command=self._chat_canvas.yview,
            bg=BG_PANEL, troughcolor=BG_DARK, width=8,
        )
        self._chat_frame = tk.Frame(self._chat_canvas, bg=BG_DARK)

        self._chat_frame.bind("<Configure>", lambda e: self._chat_canvas.configure(
            scrollregion=self._chat_canvas.bbox("all")
        ))

        self._chat_canvas.create_window((0, 0), window=self._chat_frame, anchor="nw", tags="chat_frame")
        self._chat_canvas.configure(yscrollcommand=self._chat_scrollbar.set)
        self._chat_canvas.bind("<Configure>", self._on_canvas_resize)
        self._chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Welcome
        stt_str = "ON" if self._voice_status["stt"] else "OFF"
        tts_str = "ON" if self._voice_status["tts"] else "OFF"
        self._add_system_message(f"Jarvis OS v0.1.0 | Voice: STT {stt_str}, TTS {tts_str}")
        self._add_system_message("Connecting to brain...")

        # --- Input area ---
        input_container = tk.Frame(self._root, bg=BG_PANEL, height=65)
        input_container.pack(fill=tk.X, side=tk.BOTTOM)
        input_container.pack_propagate(False)

        input_inner = tk.Frame(input_container, bg=BG_INPUT)
        input_inner.pack(fill=tk.X, padx=12, pady=10)

        # Mic button (left)
        self._mic_btn = tk.Label(
            input_inner, text="\U0001F3A4", font=("Segoe UI", 16),
            bg=BG_INPUT, fg=MIC_IDLE, cursor="hand2", padx=8, pady=4,
        )
        if self._voice_status["stt"]:
            self._mic_btn.pack(side=tk.LEFT)
            self._mic_btn.bind("<Button-1>", self._on_mic_click)
            self._mic_btn.bind("<Enter>", lambda e: self._mic_btn.configure(fg=ACCENT_HOVER) if not self._listening else None)
            self._mic_btn.bind("<Leave>", lambda e: self._mic_btn.configure(fg=MIC_IDLE) if not self._listening else None)

        # Text input
        self._input_var = tk.StringVar()
        self._input_entry = tk.Entry(
            input_inner,
            textvariable=self._input_var,
            font=("Segoe UI", 11),
            bg=BG_INPUT, fg=TEXT_PRIMARY,
            insertbackground=ACCENT,
            relief=tk.FLAT, bd=8,
        )
        self._input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._input_entry.bind("<Return>", self._on_send)
        self._input_entry.focus_set()

        # Send button (right)
        send_btn = tk.Label(
            input_inner, text="\u27A4", font=("Segoe UI", 14),
            bg=BG_INPUT, fg=ACCENT, cursor="hand2", padx=10, pady=4,
        )
        send_btn.pack(side=tk.RIGHT)
        send_btn.bind("<Button-1>", self._on_send)
        send_btn.bind("<Enter>", lambda e: send_btn.configure(fg=ACCENT_HOVER))
        send_btn.bind("<Leave>", lambda e: send_btn.configure(fg=ACCENT))

        # Keyboard shortcut: Ctrl+Space for voice
        self._root.bind("<Control-space>", self._on_mic_click)

    def _on_canvas_resize(self, event: Any) -> None:
        self._chat_canvas.itemconfig("chat_frame", width=event.width)

    def _on_mousewheel(self, event: Any) -> None:
        self._chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _add_message(self, role: str, text: str) -> None:
        """Add a chat message bubble."""
        is_user = role == "user"
        bubble_bg = BG_MSG_USER if is_user else BG_MSG_JARVIS
        name = "You" if is_user else "Jarvis"
        name_color = TEXT_SECONDARY if is_user else ACCENT
        timestamp = datetime.now().strftime("%H:%M")

        row = tk.Frame(self._chat_frame, bg=BG_DARK)
        row.pack(fill=tk.X, padx=12, pady=(4, 2))

        bubble = tk.Frame(row, bg=bubble_bg, padx=12, pady=8)
        bubble.pack(fill=tk.X)

        header = tk.Frame(bubble, bg=bubble_bg)
        header.pack(fill=tk.X)

        tk.Label(
            header, text=name, font=("Segoe UI", 9, "bold"),
            bg=bubble_bg, fg=name_color, anchor="w",
        ).pack(side=tk.LEFT)

        tk.Label(
            header, text=timestamp, font=("Segoe UI", 8),
            bg=bubble_bg, fg=TEXT_DIM, anchor="e",
        ).pack(side=tk.RIGHT)

        msg_label = tk.Label(
            bubble, text=text, font=("Segoe UI", 10),
            bg=bubble_bg, fg=TEXT_PRIMARY,
            wraplength=370, justify=tk.LEFT, anchor="nw",
        )
        msg_label.pack(fill=tk.X, pady=(4, 0))

        self._messages.append({"role": role, "text": text})
        self._chat_frame.update_idletasks()
        self._chat_canvas.yview_moveto(1.0)

    def _add_system_message(self, text: str) -> None:
        row = tk.Frame(self._chat_frame, bg=BG_DARK)
        row.pack(fill=tk.X, padx=12, pady=(6, 2))
        tk.Label(
            row, text=text, font=("Segoe UI", 9, "italic"),
            bg=BG_DARK, fg=TEXT_DIM, anchor="center",
        ).pack()
        self._chat_frame.update_idletasks()
        self._chat_canvas.yview_moveto(1.0)

    def _update_status(self, connected: bool) -> None:
        self._connected = connected
        if connected:
            self._status_dot.configure(fg=GREEN)
            self._status_label.configure(text="Connected")
        else:
            self._status_dot.configure(fg=RED)
            self._status_label.configure(text="Disconnected")

    # --- Input handling ---

    def _on_send(self, event: Any = None) -> None:
        text = self._input_var.get().strip()
        if not text:
            return
        self._input_var.set("")
        self._send_text(text)

    def _send_text(self, text: str) -> None:
        """Send text to brain and display in chat."""
        self._add_message("user", text)
        if self._loop and self._connected:
            asyncio.run_coroutine_threadsafe(self._send_to_brain(text), self._loop)
        elif not self._connected:
            self._add_system_message("Not connected to brain.")

    # --- Voice ---

    def _on_mic_click(self, event: Any = None) -> None:
        """Handle mic button click -- start listening in a thread."""
        if self._listening or not self._voice.stt_ready:
            return

        self._listening = True
        self._mic_btn.configure(fg=MIC_ACTIVE)
        self._add_system_message("\U0001F3A4 Listening... speak now")

        threading.Thread(target=self._do_listen, daemon=True).start()

    def _do_listen(self) -> None:
        """Run speech recognition in a background thread."""
        text = self._voice.listen(timeout=8, phrase_limit=15)

        self._listening = False
        self._root.after(0, self._mic_btn.configure, {"fg": MIC_IDLE})

        if text:
            self._root.after(0, self._send_text, text)
        else:
            self._root.after(0, self._add_system_message, "Didn't catch that. Try again.")

    # --- WebSocket ---

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
                        self._root.after(0, self._update_status, True)
                        self._root.after(0, self._add_system_message, "Connected to brain.")
                        reconnect_delay = 1.0

                    async for raw in ws:
                        msg = json.loads(raw)
                        await self._handle_message(msg)

            except Exception as e:
                self._ws = None
                self._root.after(0, self._update_status, False)
                log.warning("Connection lost: %s. Retry in %.0fs", e, reconnect_delay)
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30.0)

    async def _send_to_brain(self, text: str) -> None:
        if self._ws:
            try:
                await self._ws.send(json.dumps({
                    "event": "user_input",
                    "device_id": self._device_id,
                    "text": text,
                }))
            except Exception as e:
                self._root.after(0, self._add_system_message, f"Send failed: {e}")

    async def _handle_message(self, msg: dict) -> None:
        event = msg.get("event", "")

        if event == "response":
            text = msg.get("text", "")
            if text:
                self._root.after(0, self._add_message, "jarvis", text)
                # Speak the response
                if msg.get("tts", False) and self._voice.tts_ready:
                    self._voice.speak(text)

            actions = msg.get("actions", [])
            for act in actions:
                await self._execute_action(act)

        elif event == "notification":
            text = msg.get("message", "")
            self._root.after(0, self._add_system_message, f"[Notification] {text}")

        elif event == "pending_task":
            task = msg.get("task", {})
            self._root.after(0, self._add_system_message,
                             f"[Pending] {task.get('description', '')}")

    async def _execute_action(self, action: dict) -> None:
        from agents.windows.actions import apps, browser, clipboard, files, system, terminal

        action_type = action.get("type", "")
        target = action.get("target", "")
        params = action.get("params", {})
        success, details = False, "Unknown action"

        if action_type == "open_app":
            success, details = apps.open_app(target)
        elif action_type == "close_app":
            success, details = apps.close_app(target)
        elif action_type == "open_url":
            success, details = browser.open_url(target)
        elif action_type == "search":
            success, details = browser.search_web(target)
        elif action_type == "volume":
            success, details = system.set_volume(target)
        elif action_type == "system_power":
            if target == "lock":
                success, details = system.lock_screen()
        elif action_type == "terminal":
            success, details = terminal.run_command(target)
        elif action_type == "clipboard":
            op = params.get("operation", "read")
            if op == "write":
                success, details = clipboard.write_clipboard(target)

        status_text = f"[Action] {action_type} {target}: {'OK' if success else 'FAIL'}"
        self._root.after(0, self._add_system_message, status_text)

    # --- System tray ---

    def _run_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw

            def create_icon() -> Image.Image:
                img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                draw.ellipse([4, 4, 60, 60], fill=(99, 102, 241, 255))
                try:
                    draw.text((22, 16), "J", fill=(255, 255, 255, 255))
                except Exception:
                    pass
                return img

            def show_window(icon, item):
                self._root.after(0, self._show_window)

            def quit_app(icon, item):
                self._running = False
                icon.stop()
                self._root.after(0, self._root.destroy)

            menu = pystray.Menu(
                pystray.MenuItem("Show Jarvis", show_window, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", quit_app),
            )

            icon = pystray.Icon("jarvis", create_icon(), "Jarvis OS", menu)
            icon.run()

        except ImportError:
            log.warning("pystray/Pillow not installed. No tray icon.")

    def _show_window(self) -> None:
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()
        self._input_entry.focus_set()

    def _hide_window(self) -> None:
        self._root.withdraw()

    def run(self) -> None:
        self._root.after(100, self._show_window)
        self._root.mainloop()


def main() -> None:
    app = JarvisApp()
    app.run()


if __name__ == "__main__":
    main()
