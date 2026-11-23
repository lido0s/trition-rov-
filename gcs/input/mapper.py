"""Dead-zones and mapping of raw device states to named commands (R5, R8)."""
from __future__ import annotations

import logging
import threading
import time
from types import MappingProxyType
from typing import Any, Optional

from gcs.core.interfaces import ConfigProvider, DeviceState, MessageBus
from gcs.core.messages import InputFrame, Topics

log = logging.getLogger(__name__)


def apply_deadzone(value: float, deadzone: float) -> float:
    """Zero inside the dead-zone; rescale the rest so output still reaches +-1."""
    deadzone = min(deadzone, 0.99)
    if abs(value) < deadzone:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) - deadzone) / (1.0 - deadzone)


class InputMapper:
    def __init__(self, config: ConfigProvider, bus: MessageBus) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._controller: Optional[str] = None
        self._profile_name, self._profile = config.profile_for(None)
        bus.subscribe(Topics.DEVICE_CONNECTED, lambda event: self._select(event.name))
        bus.subscribe(Topics.DEVICE_DISCONNECTED, lambda _: self._select(None))
        bus.subscribe(Topics.CONFIG_RELOADED, self._reload)

    def _select(self, controller: Optional[str]) -> None:
        name, profile = self._config.profile_for(controller)  # auto-profile per controller (R8)
        with self._lock:
            self._controller, self._profile_name, self._profile = controller, name, profile
        log.info("Active profile: %s", name)

    def _reload(self, _: Any) -> None:
        with self._lock:
            controller = self._controller
        self._select(controller)

    @property
    def profile_name(self) -> str:
        with self._lock:
            return self._profile_name

    def map(self, states: list[DeviceState]) -> InputFrame:
        with self._lock:
            profile = self._profile
        commands: dict[str, float] = {}
        pressed: set[str] = set()
        for state in states:
            if state.source == "gamepad":
                self._gamepad(state, profile, commands, pressed)
        for state in states:  # keyboard adds on top of the gamepad
            if state.source == "keyboard":
                self._keyboard(state, profile, commands)
        return InputFrame(time.time(), MappingProxyType(commands), frozenset(pressed))

    @staticmethod
    def _gamepad(state, profile, commands, pressed) -> None:
        for index, spec in profile.get("axes", {}).items():
            raw = state.axes.get(int(index))
            if raw is not None:
                raw = -raw if spec.get("invert") else raw
                commands[spec["command"]] = apply_deadzone(raw, spec.get("deadzone", 0.1))
        for index, name in profile.get("buttons", {}).items():
            if int(index) in state.buttons:
                pressed.add(name)
        for index, spec in profile.get("hats", {}).items():
            x, y = state.hats.get(int(index), (0, 0))
            for direction, active in (("up", y == 1), ("down", y == -1),
                                      ("left", x == -1), ("right", x == 1)):
                if active and direction in spec:
                    pressed.add(spec[direction])

    @staticmethod
    def _keyboard(state, profile, commands) -> None:
        for key in state.keys:
            if key in profile.get("keys", {}):
                command, value = profile["keys"][key]
                commands[command] = max(-1.0, min(1.0, commands.get(command, 0.0) + value))
