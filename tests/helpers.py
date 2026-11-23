import copy
import json
import time

CONFIG = {
    "input": {"sample_rate_hz": 50},
    "default_profile": "default",
    "profiles": {
        "default": {
            "controller_name": None,
            "axes": {
                "0": {"command": "sway", "deadzone": 0.1},
                "1": {"command": "surge", "deadzone": 0.1, "invert": True},
            },
            "buttons": {"0": "lights"},
            "hats": {"0": {"up": "u", "down": "d", "left": "l", "right": "r"}},
            "keys": {"w": ["surge", 1.0]},
        }
    },
}


def write_config(path, data=None):
    path.write_text(json.dumps(data or CONFIG, indent=2))
    return str(path)


def edited(change):
    """A copy of CONFIG after change(data) modified it."""
    data = copy.deepcopy(CONFIG)
    change(data)
    return data


def wait_for(predicate, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return False
