"""Abstract interfaces modules depend on instead of each other (R17, R18)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol


@dataclass
class DeviceState:
    """Raw snapshot of one device (only used inside the sampler thread)."""

    source: str  # "gamepad" or "keyboard"
    name: str = ""
    axes: dict[int, float] = field(default_factory=dict)
    buttons: set[int] = field(default_factory=set)
    hats: dict[int, tuple[int, int]] = field(default_factory=dict)
    keys: set[str] = field(default_factory=set)


class MessageBus(Protocol):
    def subscribe(self, topic: str, handler: Callable[[Any], None]) -> None:
        ...

    def publish(self, topic: str, payload: Any = None) -> None:
        ...


class InputDevice(ABC):
    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def poll(self) -> Optional[DeviceState]:
        """Current state, or None if the device is absent."""


class ConfigProvider(ABC):
    @property
    @abstractmethod
    def sample_rate(self) -> float:
        ...

    @abstractmethod
    def profile_for(self, controller_name: Optional[str]) -> tuple[str, dict]:
        """(profile_name, profile) for a controller, or the default profile."""
