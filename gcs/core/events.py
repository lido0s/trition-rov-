"""Thread-safe publish/subscribe bus (R15, R18).

publish() never blocks: events go into a bounded queue.Queue and the bus thread
delivers them to subscribers.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable

from gcs.core.service import ThreadService

log = logging.getLogger(__name__)


class EventBus(ThreadService):
    def __init__(self, maxsize: int = 1000) -> None:
        super().__init__("EventBus")
        self._subs: dict[str, list[Callable[[Any], None]]] = {}
        self._lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)

    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        with self._lock:
            self._subs.setdefault(topic, []).append(handler)

    def publish(self, topic: str, payload: Any = None) -> None:
        try:
            self._queue.put_nowait((topic, payload))
        except queue.Full:
            log.warning("Event queue full, dropped '%s'", topic)

    def run(self) -> None:
        while not self._stop_evt.is_set():
            try:
                topic, payload = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            with self._lock:
                handlers = list(self._subs.get(topic, []))
            for handler in handlers:
                try:
                    handler(payload)
                except Exception:
                    log.exception("Handler failed for topic '%s'", topic)
