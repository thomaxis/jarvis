"""Audio device management utilities."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("jarvis.audio")


def list_audio_devices() -> list[dict]:
    """List available audio input/output devices."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        devices = []
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            devices.append({
                "index": i,
                "name": info.get("name", ""),
                "input_channels": info.get("maxInputChannels", 0),
                "output_channels": info.get("maxOutputChannels", 0),
                "default_sample_rate": info.get("defaultSampleRate", 0),
            })
        pa.terminate()
        return devices
    except ImportError:
        log.warning("pyaudio not installed")
        return []


def get_default_input_device() -> int | None:
    """Get the index of the default input device."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        info = pa.get_default_input_device_info()
        idx = info.get("index")
        pa.terminate()
        return idx
    except Exception:
        return None


def get_default_output_device() -> int | None:
    """Get the index of the default output device."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        info = pa.get_default_output_device_info()
        idx = info.get("index")
        pa.terminate()
        return idx
    except Exception:
        return None
