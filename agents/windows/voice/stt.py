"""Speech-to-Text using faster-whisper. Runs locally on-device."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("jarvis.stt")


class SpeechToText:
    """Local STT using faster-whisper."""

    def __init__(self, model_size: str = "base.en") -> None:
        self._model: Any = None
        self._model_size = model_size
        self._enabled = False

    def initialize(self) -> bool:
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(self._model_size, device="cpu", compute_type="int8")
            self._enabled = True
            log.info("STT initialized (model: %s)", self._model_size)
            return True
        except ImportError:
            log.warning("faster-whisper not installed. STT disabled.")
            return False
        except Exception as e:
            log.error("STT init failed: %s", e)
            return False

    @property
    def enabled(self) -> bool:
        return self._enabled

    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text."""
        if not self._model:
            return ""

        try:
            segments, info = self._model.transcribe(audio_path, beam_size=5)
            text = " ".join(segment.text.strip() for segment in segments)
            log.info("Transcribed: %s (%.1fs audio)", text[:60], info.duration)
            return text.strip()
        except Exception as e:
            log.error("Transcription failed: %s", e)
            return ""

    def transcribe_bytes(self, audio_bytes: bytes, sample_rate: int = 16000) -> str:
        """Transcribe raw audio bytes."""
        if not self._model:
            return ""

        try:
            import io
            import numpy as np
            audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, info = self._model.transcribe(audio_array, beam_size=5)
            text = " ".join(segment.text.strip() for segment in segments)
            return text.strip()
        except Exception as e:
            log.error("Byte transcription failed: %s", e)
            return ""
