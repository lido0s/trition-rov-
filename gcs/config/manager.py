"""JSON config with named profiles, saved/loaded while running (R8, R19)."""
from __future__ import annotations

import copy
import json
import logging
import threading
from pathlib import Path
from typing import Optional

from gcs.core.interfaces import ConfigProvider, MessageBus
from gcs.core.messages import Topics
from gcs.core.service import ThreadService

log = logging.getLogger(__name__)


class ConfigManager(ConfigProvider):
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._seen: Optional[tuple[int, int]] = None
        self._data: dict = {}
        if not self.load():
            raise ValueError(f"Cannot start: invalid config file {path}")

    def _signature(self) -> Optional[tuple[int, int]]:
        try:
            stat = self.path.stat()
            return (stat.st_mtime_ns, stat.st_size)
        except OSError:
            return None

    def load(self) -> bool:
        """Re-read the file. A broken file is rejected and the old settings are kept."""
        signature = self._signature()
        try:
            data = json.loads(self.path.read_text())
            data["profiles"][data.get("default_profile", "default")]  # default must exist
        except (OSError, ValueError, KeyError, TypeError) as exc:
            log.error("Config rejected, keeping previous settings: %s", exc)
            with self._lock:
                self._seen = signature  # report a bad file once, not every poll
            return False
        with self._lock:
            self._data, self._seen = data, signature
        log.info("Config loaded from %s", self.path)
        return True

    def has_changed(self) -> bool:
        signature = self._signature()
        with self._lock:
            return signature != self._seen

    def save_profile(self, name: str, profile: dict) -> None:
        """Store a mapping profile in the file; the watcher applies it live."""
        with self._lock:
            self._data["profiles"][name] = copy.deepcopy(profile)
            text = json.dumps(self._data, indent=2)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(text)
        tmp.replace(self.path)  # atomic

    def section(self, name: str) -> dict:
        with self._lock:
            return copy.deepcopy(self._data.get(name, {}))

    @property
    def sample_rate(self) -> float:
        with self._lock:
            return max(1.0, float(self._data.get("input", {}).get("sample_rate_hz", 50)))

    def profile_for(self, controller_name: Optional[str]) -> tuple[str, dict]:
        """Profile registered for this controller, else the default (R8)."""
        with self._lock:
            profiles = self._data["profiles"]
            for name, profile in profiles.items():
                if controller_name and profile.get("controller_name") == controller_name:
                    return name, copy.deepcopy(profile)
            default = self._data.get("default_profile", "default")
            return default, copy.deepcopy(profiles[default])


class ConfigWatcher(ThreadService):
    """Polls the file so the input sampler never touches the disk (R3)."""

    def __init__(self, config: ConfigManager, bus: MessageBus, interval: float = 1.0) -> None:
        super().__init__("ConfigWatcher")
        self._config, self._bus, self._interval = config, bus, interval

    def run(self) -> None:
        while not self._stop_evt.wait(self._interval):
            if self._config.has_changed() and self._config.load():
                self._bus.publish(Topics.CONFIG_RELOADED)
