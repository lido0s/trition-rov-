"""Topic names and immutable message payloads (R15)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


class Topics:
    INPUT_FRAME = "input.frame"
    INPUT_BUTTON = "input.button"
    DEVICE_CONNECTED = "device.connected"
    DEVICE_DISCONNECTED = "device.disconnected"
    CONFIG_RELOADED = "config.reloaded"


@dataclass(frozen=True)
class InputFrame:
    timestamp: float
    commands: Mapping[str, float]
    buttons: frozenset[str]


@dataclass(frozen=True)
class ButtonPressed:
    name: str


@dataclass(frozen=True)
class DeviceConnected:
    name: str
