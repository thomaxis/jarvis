"""Jarvis Windows App -- Native window with modern web-based UI.

Uses pywebview for a native Windows window with full HTML/CSS/JS control.
Connects to the brain via WebSocket. Supports voice (STT + TTS).

Usage: python agents/windows/app.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("jarvis.app")


# ── Voice Engine ──

class VoiceEngine:
    def __init__(self) -> None:
        self._recognizer = None
        self._tts_engine = None
        self.stt_ready = False
        self.tts_ready = False
        self._tts_lock = threading.Lock()

    def initialize(self) -> None:
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 1.0
            with sr.Microphone():
                pass
            self.stt_ready = True
        except Exception as e:
            log.warning("STT disabled: %s", e)
        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty("rate", 175)
            for v in self._tts_engine.getProperty("voices"):
                if "david" in v.name.lower() or "mark" in v.name.lower():
                    self._tts_engine.setProperty("voice", v.id)
                    break
            self.tts_ready = True
        except Exception as e:
            log.warning("TTS disabled: %s", e)

    def listen(self) -> str:
        if not self.stt_ready:
            return ""
        import speech_recognition as sr
        try:
            with sr.Microphone() as src:
                self._recognizer.adjust_for_ambient_noise(src, duration=0.3)
                audio = self._recognizer.listen(src, timeout=8, phrase_time_limit=15)
            return self._recognizer.recognize_google(audio)
        except Exception:
            return ""

    def speak(self, text: str) -> None:
        if not self.tts_ready:
            return
        def _do():
            with self._tts_lock:
                try:
                    self._tts_engine.say(text)
                    self._tts_engine.runAndWait()
                except Exception:
                    pass
        threading.Thread(target=_do, daemon=True).start()


# ── JS Bridge API ──

class JarvisAPI:
    """Python API exposed to the webview JS via pywebview."""

    def __init__(self) -> None:
        self._ws = None
        self._connected = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._window = None
        self._voice = VoiceEngine()
        self._listening = False

        self._device_id = os.environ.get("JARVIS_DEVICE_ID", "windows-gui")
        self._brain_ws = os.environ.get("JARVIS_BRAIN_WS", "ws://localhost:8400/ws")
        self._token = os.environ.get("JARVIS_AGENT_TOKEN", "")

    def start(self, window) -> None:
        self._window = window
        self._voice.initialize()
        self._call_js("setVoiceStatus", self._voice.stt_ready, self._voice.tts_ready)
        threading.Thread(target=self._run_async, daemon=True).start()

    def send_message(self, text: str) -> None:
        if not text.strip():
            return
        if self._loop and self._connected:
            asyncio.run_coroutine_threadsafe(self._ws_send(text), self._loop)

    def start_listening(self) -> None:
        if self._listening or not self._voice.stt_ready:
            return
        self._listening = True
        self._call_js("setListening", True)
        threading.Thread(target=self._do_listen, daemon=True).start()

    def get_status(self) -> dict:
        return {"connected": self._connected, "stt": self._voice.stt_ready, "tts": self._voice.tts_ready}

    # ── Internal ──

    def _do_listen(self) -> None:
        text = self._voice.listen()
        self._listening = False
        self._call_js("setListening", False)
        if text:
            self._call_js("onVoiceResult", text)
        else:
            self._call_js("onVoiceFail")

    def _call_js(self, fn: str, *args: Any) -> None:
        if self._window:
            try:
                args_str = ", ".join(json.dumps(a) for a in args)
                self._window.evaluate_js(f"window.jarvisUI.{fn}({args_str})")
            except Exception:
                pass

    def _run_async(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect_loop())

    async def _connect_loop(self) -> None:
        import websockets
        delay = 1.0
        while True:
            try:
                hdrs = {"Authorization": f"Bearer {self._token}"} if self._token else {}
                async with websockets.connect(self._brain_ws, additional_headers=hdrs) as ws:
                    self._ws = ws
                    await ws.send(json.dumps({
                        "event": "agent_connect", "device_id": self._device_id,
                        "platform": "windows",
                        "capabilities": ["os_control", "apps", "files", "browser", "terminal", "clipboard", "system", "voice"],
                    }))
                    raw = await ws.recv()
                    if json.loads(raw).get("event") == "connected":
                        self._connected = True
                        self._call_js("setConnected", True)
                        delay = 1.0
                    async for raw in ws:
                        msg = json.loads(raw)
                        await self._handle(msg)
            except Exception as e:
                self._ws = None
                self._connected = False
                self._call_js("setConnected", False)
                log.warning("WS lost: %s, retry %.0fs", e, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)

    async def _ws_send(self, text: str) -> None:
        if self._ws:
            await self._ws.send(json.dumps({"event": "user_input", "device_id": self._device_id, "text": text}))

    async def _handle(self, msg: dict) -> None:
        ev = msg.get("event", "")
        if ev == "response":
            text = msg.get("text", "")
            if text:
                self._call_js("addMessage", "jarvis", text)
                if msg.get("tts") and self._voice.tts_ready:
                    self._voice.speak(text)
            for act in msg.get("actions", []):
                await self._exec(act)
        elif ev == "notification":
            self._call_js("addSystem", msg.get("message", ""))

    async def _exec(self, action: dict) -> None:
        from agents.windows.actions import apps, browser, clipboard, files, system, terminal
        t, target, p = action.get("type", ""), action.get("target", ""), action.get("params", {})
        ok, d = False, ""
        if t == "open_app": ok, d = apps.open_app(target)
        elif t == "close_app": ok, d = apps.close_app(target)
        elif t == "open_url": ok, d = browser.open_url(target)
        elif t == "search": ok, d = browser.search_web(target)
        elif t == "volume": ok, d = system.set_volume(target)
        elif t == "terminal": ok, d = terminal.run_command(target)
        self._call_js("addSystem", f"{'Done' if ok else 'Failed'}: {t} {target}")


# ── HTML/CSS/JS ──

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg: #08080f;
  --bg-secondary: #0d0d18;
  --bg-tertiary: #111122;
  --bg-hover: #16162a;
  --surface: #13132a;
  --surface-light: #1a1a36;
  --border: #1e1e3d;
  --border-light: #2a2a50;
  --accent: #6366f1;
  --accent-glow: #818cf880;
  --accent-dim: #4f46e5;
  --green: #34d399;
  --red: #f87171;
  --text: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-dim: #475569;
  --user-bubble: #1a1a40;
  --jarvis-bubble: #0f1a2e;
  --jarvis-border: #1a2a4a;
}

body {
  font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

/* ── Header ── */
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.logo {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, var(--accent), var(--accent-dim));
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 16px; color: white;
  box-shadow: 0 0 20px var(--accent-glow);
}
.brand { font-size: 18px; font-weight: 600; letter-spacing: 0.5px; }
.status {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--text-dim); font-weight: 400;
}
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--red);
  transition: background 0.3s;
}
.status-dot.on { background: var(--green); box-shadow: 0 0 8px var(--green); }

.header-right { display: flex; align-items: center; gap: 12px; }
.badge {
  font-size: 11px; padding: 4px 10px; border-radius: 20px;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--text-dim); font-weight: 500;
}
.badge.active { color: var(--green); border-color: #1a3a2a; background: #0a1a14; }

/* ── Chat ── */
.chat {
  flex: 1; overflow-y: auto; padding: 20px 24px;
  display: flex; flex-direction: column; gap: 6px;
  scroll-behavior: smooth;
}
.chat::-webkit-scrollbar { width: 6px; }
.chat::-webkit-scrollbar-track { background: transparent; }
.chat::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.chat::-webkit-scrollbar-thumb:hover { background: var(--border-light); }

.message {
  display: flex; gap: 12px;
  max-width: 88%;
  animation: fadeIn 0.25s ease-out;
}
.message.user { align-self: flex-end; flex-direction: row-reverse; }
.message.jarvis { align-self: flex-start; }

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.avatar {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 600;
  flex-shrink: 0; margin-top: 2px;
}
.message.jarvis .avatar {
  background: linear-gradient(135deg, var(--accent), var(--accent-dim));
  color: white;
}
.message.user .avatar {
  background: var(--surface-light);
  color: var(--text-secondary);
}

.bubble {
  padding: 12px 16px;
  border-radius: 16px;
  font-size: 13.5px; line-height: 1.55;
  word-wrap: break-word;
}
.message.user .bubble {
  background: var(--user-bubble);
  border: 1px solid var(--border);
  border-bottom-right-radius: 4px;
}
.message.jarvis .bubble {
  background: var(--jarvis-bubble);
  border: 1px solid var(--jarvis-border);
  border-bottom-left-radius: 4px;
}

.bubble .name {
  font-size: 11px; font-weight: 600;
  margin-bottom: 4px;
  display: flex; justify-content: space-between;
}
.message.jarvis .name span:first-child { color: var(--accent); }
.message.user .name span:first-child { color: var(--text-secondary); }
.name .time { color: var(--text-dim); font-weight: 400; }

.system-msg {
  text-align: center; font-size: 11px; color: var(--text-dim);
  padding: 8px 0;
  animation: fadeIn 0.2s ease-out;
}

.typing {
  display: none; align-self: flex-start; padding: 6px 0;
  animation: fadeIn 0.2s ease-out;
}
.typing.show { display: flex; }
.typing-dots { display: flex; gap: 4px; padding: 10px 16px; background: var(--jarvis-bubble); border-radius: 16px; border: 1px solid var(--jarvis-border); }
.typing-dots span {
  width: 6px; height: 6px; border-radius: 50%; background: var(--text-dim);
  animation: bounce 1.2s infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.15s; }
.typing-dots span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* ── Input ── */
.input-area {
  padding: 16px 24px 20px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}
.input-row {
  display: flex; align-items: center; gap: 10px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 6px 6px 6px 8px;
  transition: border-color 0.2s;
}
.input-row:focus-within { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }

.mic-btn {
  width: 38px; height: 38px; border-radius: 50%;
  background: var(--surface); border: 1px solid var(--border);
  color: var(--accent); font-size: 16px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; flex-shrink: 0;
}
.mic-btn:hover { background: var(--bg-hover); border-color: var(--accent); }
.mic-btn.recording {
  background: var(--red); border-color: var(--red); color: white;
  animation: pulse 1.5s infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(248,113,113,0.4); }
  50% { box-shadow: 0 0 0 10px rgba(248,113,113,0); }
}

.input-field {
  flex: 1; border: none; outline: none;
  background: transparent; color: var(--text);
  font-size: 14px; font-family: inherit;
  padding: 8px 4px;
}
.input-field::placeholder { color: var(--text-dim); }

.send-btn {
  width: 38px; height: 38px; border-radius: 50%;
  background: var(--accent); border: none;
  color: white; font-size: 15px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  transition: all 0.15s; flex-shrink: 0;
}
.send-btn:hover { background: var(--accent-dim); transform: scale(1.05); }
.send-btn:active { transform: scale(0.95); }

/* ── Helpers ── */
.hidden { display: none !important; }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-left">
    <div class="logo">J</div>
    <span class="brand">Jarvis</span>
    <div class="status">
      <div class="status-dot" id="statusDot"></div>
      <span id="statusText">Connecting...</span>
    </div>
  </div>
  <div class="header-right">
    <div class="badge" id="voiceBadge">Voice OFF</div>
  </div>
</div>

<!-- Chat -->
<div class="chat" id="chat">
  <div class="system-msg">Welcome to Jarvis OS</div>
  <div class="system-msg">Connecting to brain...</div>
</div>

<!-- Typing indicator -->
<div class="typing" id="typing">
  <div style="width:32px"></div>
  <div class="typing-dots"><span></span><span></span><span></span></div>
</div>

<!-- Input -->
<div class="input-area">
  <div class="input-row">
    <button class="mic-btn" id="micBtn" onclick="window.jarvisUI.micClick()" title="Push to talk (Ctrl+Space)">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="1" width="6" height="11" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><line x1="12" y1="19" x2="12" y2="23"/></svg>
    </button>
    <input class="input-field" id="inputField" type="text" placeholder="Message Jarvis..." autocomplete="off" />
    <button class="send-btn" id="sendBtn" onclick="window.jarvisUI.sendClick()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
    </button>
  </div>
</div>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('inputField');
const micBtn = document.getElementById('micBtn');
const typing = document.getElementById('typing');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const voiceBadge = document.getElementById('voiceBadge');

window.jarvisUI = {
  // Called from Python
  setConnected(on) {
    statusDot.classList.toggle('on', on);
    statusText.textContent = on ? 'Connected' : 'Disconnected';
    if (on) this.addSystem('Brain connected. Ready.');
  },
  setVoiceStatus(stt, tts) {
    if (stt) {
      voiceBadge.textContent = 'Voice ON';
      voiceBadge.classList.add('active');
      micBtn.classList.remove('hidden');
    } else {
      voiceBadge.textContent = 'Voice OFF';
      micBtn.classList.add('hidden');
    }
  },
  setListening(on) {
    micBtn.classList.toggle('recording', on);
    if (on) this.addSystem('Listening... speak now');
  },
  onVoiceResult(text) {
    this.addMessage('user', text);
    this._send(text);
  },
  onVoiceFail() {
    this.addSystem("Didn't catch that. Try again.");
  },

  addMessage(role, text) {
    typing.classList.remove('show');
    const isUser = role === 'user';
    const now = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    const div = document.createElement('div');
    div.className = 'message ' + (isUser ? 'user' : 'jarvis');
    div.innerHTML = `
      <div class="avatar">${isUser ? 'U' : 'J'}</div>
      <div class="bubble">
        <div class="name"><span>${isUser ? 'You' : 'Jarvis'}</span><span class="time">${now}</span></div>
        <div>${this._escapeHtml(text)}</div>
      </div>
    `;
    chat.appendChild(div);
    this._scroll();
  },

  addSystem(text) {
    const div = document.createElement('div');
    div.className = 'system-msg';
    div.textContent = text;
    chat.appendChild(div);
    this._scroll();
  },

  // UI handlers
  sendClick() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    this.addMessage('user', text);
    this._send(text);
  },
  micClick() {
    pywebview.api.start_listening();
  },

  _send(text) {
    typing.classList.add('show');
    this._scroll();
    pywebview.api.send_message(text);
  },
  _scroll() {
    setTimeout(() => chat.scrollTop = chat.scrollHeight, 50);
  },
  _escapeHtml(t) {
    const d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML.replace(/\\n/g, '<br>');
  }
};

// Keyboard
input.addEventListener('keydown', e => { if (e.key === 'Enter') window.jarvisUI.sendClick(); });
document.addEventListener('keydown', e => {
  if (e.ctrlKey && e.code === 'Space') { e.preventDefault(); window.jarvisUI.micClick(); }
});
input.focus();
</script>
</body>
</html>"""


# ── Main ──

def main() -> None:
    import webview

    api = JarvisAPI()

    window = webview.create_window(
        "Jarvis",
        html=HTML,
        js_api=api,
        width=500,
        height=750,
        min_size=(420, 550),
        background_color="#08080f",
        frameless=False,
        easy_drag=False,
        text_select=True,
    )

    def on_loaded():
        api.start(window)

    window.events.loaded += on_loaded

    # System tray in background
    def run_tray():
        try:
            import pystray
            from PIL import Image, ImageDraw, ImageFont
            sz = 64
            img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([2, 2, sz-2, sz-2], radius=14, fill=(99, 102, 241, 255))
            try:
                fnt = ImageFont.truetype("segoeuib.ttf", 32)
                d.text((sz//2, sz//2), "J", fill="white", font=fnt, anchor="mm")
            except Exception:
                d.text((20, 14), "J", fill="white")

            def show_win(icon, item):
                window.show()
            def quit_app(icon, item):
                icon.stop()
                window.destroy()

            menu = pystray.Menu(
                pystray.MenuItem("Show Jarvis", show_win, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", quit_app),
            )
            pystray.Icon("jarvis", img, "Jarvis OS", menu).run()
        except ImportError:
            pass

    threading.Thread(target=run_tray, daemon=True).start()

    webview.start(debug=False)


if __name__ == "__main__":
    main()
