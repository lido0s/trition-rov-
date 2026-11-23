import json

from gcs.config.manager import ConfigManager, ConfigWatcher
from gcs.core.events import EventBus
from gcs.core.messages import Topics
from tests.helpers import wait_for, write_config


def test_profile_selected_by_controller_else_default(tmp_path):
    config = ConfigManager(write_config(tmp_path / "c.json"))
    _, default = config.profile_for(None)
    config.save_profile("xbox", {**default, "controller_name": "Xbox Pad"})
    assert config.load()
    assert config.profile_for("Xbox Pad")[0] == "xbox"
    assert config.profile_for("Other Pad")[0] == "default"


def test_broken_file_is_rejected_and_old_settings_kept(tmp_path):
    path = tmp_path / "c.json"
    config = ConfigManager(write_config(path))
    path.write_text("{ not json")
    assert config.has_changed()
    assert config.load() is False
    assert not config.has_changed()  # reported once, not every poll
    assert config.profile_for(None)[0] == "default"


def test_watcher_announces_edits(tmp_path):
    path = tmp_path / "c.json"
    config = ConfigManager(write_config(path))
    bus, events = EventBus(), []
    bus.subscribe(Topics.CONFIG_RELOADED, events.append)
    watcher = ConfigWatcher(config, bus, 0.05)
    bus.start()
    watcher.start()
    data = json.loads(path.read_text())
    data["input"]["sample_rate_hz"] = 25
    path.write_text(json.dumps(data))
    assert wait_for(lambda: events)
    assert config.sample_rate == 25
    watcher.stop()
    bus.stop()
