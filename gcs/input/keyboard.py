"""Keyboard as a second simultaneous device (R2): key down / key up."""
from __future__ import annotations

import logging
import threading
from typing import Optional

from gcs.core.interfaces import DeviceState, InputDevice

try:
    from pynput import keyboard as pynput_keyboard
except Exception:  # package missing or no display server
    pynput_keyboard = None

log = logging.getLogger(__name__)


class KeyboardDevice(InputDevice):
    def __init__(self) -> None:
        self._pressed: set[str] = set()
        self._lock = threading.Lock()
        self._listener = None

    def start(self) -> None:
        if pynput_keyboard is None:
            log.warning("pynput unavailable: keyboard input disabled")
            return
        self._listener = pynput_keyboard.Listener(
            on_press=lambda k: self._update(k, True),
            on_release=lambda k: self._update(k, False),
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()

    def poll(self) -> Optional[DeviceState]:
        if self._listener is None:
            return None
        with self._lock:
            return DeviceState(source="keyboard", name="keyboard", keys=set(self._pressed))

    def _update(self, key, down: bool) -> None:
        name = (getattr(key, "char", None) or str(key).replace("Key.", "")).lower()
        with self._lock:
            if down:
                self._pressed.add(name)
            else:
                self._pressed.discard(name)
