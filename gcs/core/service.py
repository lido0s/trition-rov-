"""Base class for every concurrent service (R14): a daemon thread with start()/stop()."""
from __future__ import annotations

import threading


class ThreadService(threading.Thread):
    def __init__(self, name: str) -> None:
        super().__init__(name=name, daemon=True)
        self._stop_evt = threading.Event()

    def stop(self) -> None:
        self._stop_evt.set()
        if self.is_alive():
            self.join(timeout=2)
