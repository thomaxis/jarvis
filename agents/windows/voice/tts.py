"""Text-to-Speech: Piper (local) or ElevenLabs (cloud)."""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger("jarvis.tts")


class TextToSpeech:
    """TTS engine with local (Piper) and cloud (ElevenLabs) options."""

    def __init__(
        self,
        engine: str = "piper",
        voice: str = "en_US-lessac-medium",
        piper_path: str | None = None,
    ) -> None:
        self._engine = engine
        self._voice = voice
        self._piper_path = piper_path
        self._enabled = False
        self._eleven_client: Any = None

    def initialize(self) -> bool:
        if self._engine == "piper":
            return self._init_piper()
        elif self._engine == "elevenlabs":
            return self._init_elevenlabs()
        else:
            log.warning("Unknown TTS engine: %s", self._engine)
            return False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def speak(self, text: str) -> bool:
        """Convert text to speech and play it."""
        if not self._enabled:
            log.warning("TTS not initialized")
            return False

        if self._engine == "piper":
            return self._speak_piper(text)
        elif self._engine == "elevenlabs":
            return self._speak_elevenlabs(text)
        return False

    def _init_piper(self) -> bool:
        """Initialize Piper TTS."""
        try:
            # Check if piper is available
            if self._piper_path:
                piper_exe = Path(self._piper_path)
            else:
                # Try common locations
                for candidate in ["piper", "piper.exe"]:
                    try:
                        subprocess.run([candidate, "--help"], capture_output=True, timeout=5)
                        self._piper_path = candidate
                        break
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        continue

            if self._piper_path:
                self._enabled = True
                log.info("Piper TTS initialized (voice: %s)", self._voice)
                return True
            else:
                log.warning("Piper not found. TTS disabled.")
                return False
        except Exception as e:
            log.error("Piper init failed: %s", e)
            return False

    def _init_elevenlabs(self) -> bool:
        """Initialize ElevenLabs cloud TTS."""
        try:
            import os
            api_key = os.environ.get("ELEVENLABS_API_KEY", "")
            if not api_key:
                log.warning("ELEVENLABS_API_KEY not set. TTS disabled.")
                return False

            from elevenlabs.client import ElevenLabs
            self._eleven_client = ElevenLabs(api_key=api_key)
            self._enabled = True
            log.info("ElevenLabs TTS initialized")
            return True
        except ImportError:
            log.warning("elevenlabs SDK not installed. TTS disabled.")
            return False
        except Exception as e:
            log.error("ElevenLabs init failed: %s", e)
            return False

    def _speak_piper(self, text: str) -> bool:
        """Speak using local Piper."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav_path = f.name

            # Piper: echo text | piper --model voice --output_file out.wav
            proc = subprocess.run(
                [self._piper_path, "--model", self._voice, "--output_file", wav_path],
                input=text.encode(),
                capture_output=True,
                timeout=30,
            )

            if proc.returncode == 0:
                _play_wav(wav_path)
                return True
            else:
                log.error("Piper failed: %s", proc.stderr.decode()[:200])
                return False
        except Exception as e:
            log.error("Piper speak failed: %s", e)
            return False

    def _speak_elevenlabs(self, text: str) -> bool:
        """Speak using ElevenLabs cloud."""
        try:
            audio = self._eleven_client.generate(
                text=text,
                voice=self._voice,
                model="eleven_monolingual_v1",
            )
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                for chunk in audio:
                    f.write(chunk)
                mp3_path = f.name

            _play_audio(mp3_path)
            return True
        except Exception as e:
            log.error("ElevenLabs speak failed: %s", e)
            return False


def _play_wav(path: str) -> None:
    """Play a WAV file on Windows."""
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME)
    except Exception:
        subprocess.run(["powershell", "-Command", f"(New-Object Media.SoundPlayer '{path}').PlaySync()"],
                       capture_output=True, timeout=30)


def _play_audio(path: str) -> None:
    """Play an audio file using system player."""
    try:
        subprocess.Popen(["start", "", path], shell=True)
    except Exception as e:
        log.error("Audio playback failed: %s", e)
