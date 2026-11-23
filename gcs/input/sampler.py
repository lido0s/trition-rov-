"""Fixed-rate input sampling in its own thread (R3, R14).

Only reads devices and publishes to the bus: no file, network, GUI or video work.
"""
from __future__ import annotations

import logging
import time

from gcs.core.interfaces import ConfigProvider, InputDevice, MessageBus
from gcs.core.messages import ButtonPressed, Topics
from gcs.core.service import ThreadService
from gcs.input.mapper import InputMapper

log = logging.getLogger(__name__)


class InputSampler(ThreadService):
    def __init__(
        self,
        bus: MessageBus,
        devices: list[InputDevice],
        mapper: InputMapper,
        config: ConfigProvider,
    ) -> None:
        super().__init__("InputSampler")
        self._bus, self._devices, self._mapper, self._config = bus, devices, mapper, config
        self._prev_buttons: frozenset[str] = frozenset()

    def run(self) -> None:
        for device in self._devices:  # started here: SDL wants its own thread
            try:
                device.start()
            except Exception:
                log.exception("Device failed to start: %s", type(device).__name__)
        next_tick = time.perf_counter()
        while not self._stop_evt.is_set():
            try:
                self._tick()
            except Exception:  # a bad tick must never kill input
                log.exception("Sampling tick failed; continuing")
            next_tick += 1.0 / self._config.sample_rate
            delay = next_tick - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            else:
                next_tick = time.perf_counter()  # fell behind: resync
        for device in self._devices:
            device.stop()

    def _tick(self) -> None:
        states = [s for s in (device.poll() for device in self._devices) if s is not None]
        frame = self._mapper.map(states)
        self._bus.publish(Topics.INPUT_FRAME, frame)
        for name in frame.buttons - self._prev_buttons:  # rising edges only
            self._bus.publish(Topics.INPUT_BUTTON, ButtonPressed(name))
        self._prev_buttons = frame.buttons
