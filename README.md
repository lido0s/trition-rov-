# AAST Triton ROVs - Ground Control Station (Phase 1)

Headless skeleton: event bus, JSON config with profiles, threaded operator input.

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    python -m gcs [config.json]    # run (default: configs/gcs_config.json)
    pytest                         # 12 tests
    ruff check .                   # lint

Edit `configs/gcs_config.json` while running: mappings reload without a restart.
A broken edit is rejected and logged, and the old mapping keeps working.

## Layout and dependency rules (R17, R18)

    gcs/core     contracts + infrastructure: messages, interfaces, EventBus, ThreadService, logging
    gcs/config   ConfigManager (JSON, profiles), ConfigWatcher (hot reload)
    gcs/input    GamepadDevice, KeyboardDevice, InputMapper (+ dead-zones), InputSampler
    gcs/main.py  composition root: the ONLY place that knows every concrete class

`config` and `input` depend only on `gcs.core`, never on each other. Modules talk through
`MessageBus` topics and the interfaces in `gcs/core/interfaces.py`.

## Concurrency (R14, R15)

| Service | Model | Why |
|---|---|---|
| Input polling (done) | thread (`ThreadService`) | I/O-bound, needs low latency |
| Config watcher (done) | thread (`ThreadService`) | keeps disk I/O away from the sampler |
| Event bus (done) | one worker thread | decouples publishers from slow subscribers |
| MNFLTY networking | thread (`ThreadService`) | socket I/O; asyncio may run inside it |
| MAVLink I/O | thread (`ThreadService`) | serial/UDP I/O |
| Video receive/decode | process (`multiprocessing`, later) | CPU-bound; avoids the GIL |
| GUI | main thread | most GUI toolkits require it |

Every service is a `ThreadService` with `start()`/`stop()`. `main.py` starts them in order
and stops them in reverse, so adding one is a few lines there. Cross-thread data uses only
`queue.Queue`, `threading.Event` and `Lock`. Messages are frozen dataclasses (immutable).
A CPU-heavy service such as video decoding can later use `multiprocessing` behind the same bus.

## Requirement checklist

| Req | Where |
|---|---|
| R1 gamepad axes/buttons/hats | `input/gamepad.py`, `input/mapper.py` |
| R2 keyboard down/up | `input/keyboard.py` |
| R3 fixed-rate, never blocked | `input/sampler.py`; `test_slow_subscriber_never_blocks_sampling` |
| R4 hot-plug + notify | `input/gamepad.py`, `main.py` (console alerts) |
| R5 dead-zones | `input/mapper.py` (`apply_deadzone`) |
| R8 save/load, no restart, profiles, auto-profile | `config/manager.py`, `input/mapper.py`; `test_mapping_edit_applies_without_restart`, `test_profile_autoloads_when_controller_connects` |
| R14 threads and/or processes | `core/service.py`, `main.py` |
| R15 safe communication | `core/events.py`, `core/messages.py` |
| R17 packages | see Layout |
| R18 bus + interfaces | `core/interfaces.py`, `core/events.py` |
| R19 config files | `configs/gcs_config.json` |
| Logging | `core/logging_setup.py` (levels, rotating file, console) |
| Tests / tooling | pytest + ruff in `pyproject.toml`, `requirements.txt` |
| Version control | `.gitignore` |
