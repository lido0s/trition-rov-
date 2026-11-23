import time

from gcs.core.events import EventBus
from tests.helpers import wait_for


def test_delivery_survives_a_failing_handler():
    bus, got = EventBus(), []
    bus.subscribe("x", lambda p: 1 / 0)
    bus.subscribe("x", got.append)
    bus.start()
    bus.publish("x", 42)
    assert wait_for(lambda: got == [42])
    bus.stop()


def test_publish_never_blocks_on_a_slow_subscriber():
    bus = EventBus(maxsize=200)
    bus.subscribe("x", lambda p: time.sleep(0.05))
    bus.start()
    start = time.perf_counter()
    for i in range(100):
        bus.publish("x", i)
    elapsed = time.perf_counter() - start
    bus.stop()
    assert elapsed < 0.2
