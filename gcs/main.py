"""Builds every module and connects them through the event bus."""
from __future__ import annotations

import logging
import sys
import time

from gcs.config.manager import ConfigManager, ConfigWatcher
from gcs.core.events import EventBus
from gcs.core.interfaces import MessageBus
from gcs.core.logging_setup import setup_logging
from gcs.core.messages import Topics
from gcs.input.gamepad import GamepadDevice
from gcs.input.keyboard import KeyboardDevice
from gcs.input.mapper import InputMapper
from gcs.input.sampler import InputSampler

log = logging.getLogger("gcs")


def attach_console(bus: MessageBus) -> None:
    """Operator notifications on the console (the GUI will subscribe the same way)."""
    bus.subscribe(Topics.DEVICE_CONNECTED, lambda e: print(f"[+] Controller connected: {e.name}"))
    bus.subscribe(Topics.DEVICE_DISCONNECTED, lambda _: print("[!] Controller DISCONNECTED"))
    bus.subscribe(Topics.INPUT_BUTTON, lambda e: print(f"[button] {e.name}"))
    last = {"t": 0.0}

    def show_frame(frame) -> None:  # throttled to 2 Hz
        if time.time() - last["t"] > 0.5 and any(frame.commands.values()):
            last["t"] = time.time()
            print({k: round(v, 2) for k, v in frame.commands.items()})

    bus.subscribe(Topics.INPUT_FRAME, show_frame)


def main() -> None:
    config = ConfigManager(sys.argv[1] if len(sys.argv) > 1 else "configs/gcs_config.json")
    setup_logging(**config.section("logging"))

    bus = EventBus()
    attach_console(bus)
    mapper = InputMapper(config, bus)
    devices = [GamepadDevice(bus), KeyboardDevice()]
    interval = config.section("input").get("config_poll_seconds", 1.0)

    watcher = ConfigWatcher(config, bus, interval)
    services = [bus, watcher, InputSampler(bus, devices, mapper, config)]
    for service in services:
        service.start()
    log.info("GCS Phase 1 running. Ctrl+C to quit.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for service in reversed(services):
            service.stop()
        log.info("Shut down cleanly")
