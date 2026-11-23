# AAST Triton ROVs - Ground Control Station (Phase 1)

Headless skeleton: event bus, JSON config with profiles, threaded operator input.

    python -m venv .venv && source .venv/bin/activate
    pip install -e ".[dev]"
    python -m gcs [config.json]    # run (default: configs/gcs_config.json)
    pytest                         # tests
    ruff check .                   # lint

Edit `configs/gcs_config.json` while running: mappings reload without a restart.

## Layout

    gcs/core     messages, interfaces, EventBus, ThreadService, logging
    gcs/config   ConfigManager (JSON profiles) + ConfigWatcher (hot reload)
    gcs/input    GamepadDevice, KeyboardDevice, InputMapper (+ dead-zones), InputSampler
    gcs/main.py  the only place that knows every concrete class

`config` and `input` depend only on `gcs.core` (interfaces + the bus), never on each other.
All services are `ThreadService` threads (I/O-bound work). Cross-thread data goes through
`queue.Queue`, `threading.Event` and locks, and messages are immutable. A CPU-heavy service
such as video decoding can later use `multiprocessing` behind the same bus.
