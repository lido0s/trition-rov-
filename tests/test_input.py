import json
import time

from gcs.config.manager import ConfigManager, ConfigWatcher
from gcs.core.events import EventBus
from gcs.core.interfaces import DeviceState, InputDevice
from gcs.core.messages import ButtonPressed, DeviceConnected, Topics
from gcs.input.mapper import InputMapper
from gcs.input.sampler import InputSampler
from tests.helpers import edited, wait_for, write_config


class FakePad(InputDevice):
    """The sampler only needs the InputDevice interface (R18)."""

    def __init__(self):
        self.polls = 0

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def poll(self):
        self.polls += 1
        return DeviceState(source="gamepad", axes={0: 0.05, 1: -1.0}, buttons={0})


def _setup(tmp_path, data=None):
    config = ConfigManager(write_config(tmp_path / "c.json", data))
    bus = EventBus()
    return config, bus, InputMapper(config, bus)


def test_sampler_publishes_immutable_mapped_frames(tmp_path):
    config, bus, mapper = _setup(tmp_path)
    frames, buttons = [], []
    bus.subscribe(Topics.INPUT_FRAME, frames.append)
    bus.subscribe(Topics.INPUT_BUTTON, buttons.append)
    sampler = InputSampler(bus, [FakePad()], mapper, config)
    bus.start()
    sampler.start()
    assert wait_for(lambda: len(frames) >= 3)
    sampler.stop()
    bus.stop()
    assert frames[0].commands["sway"] == 0.0     # inside the dead-zone
    assert frames[0].commands["surge"] > 0.9     # inverted axis
    assert buttons == [ButtonPressed("lights")]  # rising edge fires once
    try:
        frames[0].commands["surge"] = 0.0
        mutable = True
    except TypeError:
        mutable = False
    assert not mutable  # frames are shared across threads, so read-only (R15)


def test_slow_subscriber_never_blocks_sampling(tmp_path):
    config, bus, mapper = _setup(tmp_path)
    pad = FakePad()
    bus.subscribe(Topics.INPUT_FRAME, lambda f: time.sleep(0.3))  # hopelessly slow GUI
    sampler = InputSampler(bus, [pad], mapper, config)
    bus.start()
    sampler.start()
    time.sleep(0.6)
    sampler.stop()
    bus.stop()
    assert pad.polls >= 20  # about 50 Hz * 0.6 s = 30 (R3)


def test_profile_autoloads_when_controller_connects(tmp_path):
    data = edited(lambda d: d["profiles"].update(
        pad={**d["profiles"]["default"], "controller_name": "Pad X"}))
    _, bus, mapper = _setup(tmp_path, data)
    bus.start()
    bus.publish(Topics.DEVICE_CONNECTED, DeviceConnected("Pad X"))
    assert wait_for(lambda: mapper.profile_name == "pad")
    bus.publish(Topics.DEVICE_DISCONNECTED)
    assert wait_for(lambda: mapper.profile_name == "default")
    bus.stop()


def test_mapping_edit_applies_without_restart(tmp_path):
    config, bus, mapper = _setup(tmp_path)
    state = DeviceState(source="gamepad", axes={1: -1.0})
    watcher = ConfigWatcher(config, bus, 0.05)
    bus.start()
    watcher.start()
    assert "surge" in mapper.map([state]).commands
    renamed = edited(lambda d: d["profiles"]["default"]["axes"]["1"].update(command="forward"))
    (tmp_path / "c.json").write_text(json.dumps(renamed))
    assert wait_for(lambda: "forward" in mapper.map([state]).commands)
    watcher.stop()
    bus.stop()


def test_dpad_and_keyboard(tmp_path):
    _, bus, mapper = _setup(tmp_path)
    pad = DeviceState(source="gamepad", hats={0: (-1, 1)})
    assert mapper.map([pad]).buttons == frozenset({"u", "l"})
    keys = DeviceState(source="keyboard", keys={"w"})
    assert mapper.map([keys]).commands["surge"] == 1.0
