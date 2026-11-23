"""Game controller via pygame (R1) with hot-plug handling (R4)."""
from __future__ import annotations

import logging
import os
from typing import Optional

import pygame

from gcs.core.interfaces import DeviceState, InputDevice, MessageBus
from gcs.core.messages import DeviceConnected, Topics

log = logging.getLogger(__name__)


class GamepadDevice(InputDevice):
    def __init__(self, bus: MessageBus) -> None:
        self._bus = bus
        self._js: Optional[pygame.joystick.JoystickType] = None

    def start(self) -> None:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # headless: no window
        pygame.display.init()
        pygame.joystick.init()
        for index in range(pygame.joystick.get_count()):
            self._attach(index)

    def stop(self) -> None:
        pygame.joystick.quit()
        pygame.display.quit()

    def poll(self) -> Optional[DeviceState]:
        for event in pygame.event.get():
            if event.type == pygame.JOYDEVICEADDED:
                self._attach(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                if self._js is not None and self._js.get_instance_id() == event.instance_id:
                    self._drop()
        js = self._js
        if js is None:
            return None
        try:
            return DeviceState(
                source="gamepad",
                name=js.get_name(),
                axes={i: js.get_axis(i) for i in range(js.get_numaxes())},
                buttons={i for i in range(js.get_numbuttons()) if js.get_button(i)},
                hats={i: tuple(js.get_hat(i)) for i in range(js.get_numhats())},
            )
        except pygame.error:  # unplugged between events
            self._drop()
            return None

    def _attach(self, index: int) -> None:
        if self._js is not None:
            return
        try:
            self._js = pygame.joystick.Joystick(index)
        except pygame.error:
            log.exception("Could not open controller %s", index)
            return
        name = self._js.get_name()
        log.info("Controller connected: %s", name)
        self._bus.publish(Topics.DEVICE_CONNECTED, DeviceConnected(name))

    def _drop(self) -> None:
        if self._js is not None:
            log.warning("Controller disconnected")
            self._js = None
            self._bus.publish(Topics.DEVICE_DISCONNECTED)
