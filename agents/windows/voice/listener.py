"""Wake word detection and microphone capture."""

from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("jarvis.listener")


class VoiceListener:
    """Handles microphone capture, wake word detection, and voice activity."""

    def __init__(
        self,
        wake_word: str = "jarvis",
        silence_threshold: int = 500,
        sample_rate: int = 16000,
        channels: int = 1,
    ) -> None:
        self._wake_word = wake_word
        self._silence_threshold = silence_threshold
        self._sample_rate = sample_rate
        self._channels = channels
        self._porcupine: Any = None
        self._pyaudio: Any = None
        self._stream: Any = None
        self._enabled = False

    def initialize(self) -> bool:
        """Initialize audio capture and wake word engine."""
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            log.info("Audio capture initialized")
        except ImportError:
            log.warning("pyaudio not installed. Voice disabled.")
            return False

        # Try Porcupine for wake word
        try:
            import pvporcupine
            self._porcupine = pvporcupine.create(keywords=[self._wake_word])
            log.info("Wake word engine initialized: '%s'", self._wake_word)
        except (ImportError, Exception) as e:
            log.warning("Porcupine unavailable (%s). Using push-to-talk only.", e)
            self._porcupine = None

        self._enabled = True
        return True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def listen_for_wake_word(self, on_wake: Callable) -> None:
        """Block until wake word is detected, then call on_wake."""
        if not self._porcupine or not self._pyaudio:
            return

        import struct
        stream = self._pyaudio.open(
            rate=self._porcupine.sample_rate,
            channels=1,
            format=8,  # paInt16
            input=True,
            frames_per_buffer=self._porcupine.frame_length,
        )

        log.info("Listening for wake word '%s'...", self._wake_word)
        try:
            while True:
                pcm = stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                result = self._porcupine.process(pcm)
                if result >= 0:
                    log.info("Wake word detected!")
                    on_wake()
                    break
        finally:
            stream.stop_stream()
            stream.close()

    def record_until_silence(self, max_seconds: int = 10) -> str:
        """Record audio until silence is detected. Returns path to WAV file."""
        if not self._pyaudio:
            return ""

        import struct
        import array

        stream = self._pyaudio.open(
            rate=self._sample_rate,
            channels=self._channels,
            format=8,  # paInt16
            input=True,
            frames_per_buffer=1024,
        )

        frames = []
        silent_chunks = 0
        max_chunks = int(self._sample_rate / 1024 * max_seconds)

        log.info("Recording... (speak now)")
        try:
            for _ in range(max_chunks):
                data = stream.read(1024, exception_on_overflow=False)
                frames.append(data)

                # Check for silence
                audio_data = array.array("h", data)
                amplitude = max(abs(s) for s in audio_data) if audio_data else 0

                if amplitude < self._silence_threshold:
                    silent_chunks += 1
                    if silent_chunks > int(self._sample_rate / 1024 * 1.5):  # 1.5s silence
                        break
                else:
                    silent_chunks = 0
        finally:
            stream.stop_stream()
            stream.close()

        if not frames:
            return ""

        # Save to temporary WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(self._channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self._sample_rate)
            wf.writeframes(b"".join(frames))

        log.info("Recorded %.1f seconds", len(frames) * 1024 / self._sample_rate)
        return wav_path

    def cleanup(self) -> None:
        if self._porcupine:
            self._porcupine.delete()
        if self._pyaudio:
            self._pyaudio.terminate()
