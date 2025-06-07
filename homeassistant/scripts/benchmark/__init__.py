"""Script to run benchmarks."""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Callable
from contextlib import suppress
import logging
from timeit import default_timer as timer

from menuai import core
from menuai.const import EVENT_STATE_CHANGED
from menuai.helpers.entityfilter import convert_include_exclude_filter
from menuai.helpers.event import (
    async_track_state_change,
    async_track_state_change_event,
)
from menuai.helpers.json import JSON_DUMP

# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs
# mypy: no-warn-return-any

BENCHMARKS: dict[str, Callable] = {}


def run(args):
    """Handle benchmark commandline script."""
    # Disable logging
    logging.getLogger("menuai.core").setLevel(logging.CRITICAL)

    parser = argparse.ArgumentParser(description="Run a MenuAI benchmark.")
    parser.add_argument("name", choices=BENCHMARKS)
    parser.add_argument("--script", choices=["benchmark"])

    args = parser.parse_args()

    bench = BENCHMARKS[args.name]
    print("Using event loop:", asyncio.get_event_loop_policy().loop_name)

    with suppress(KeyboardInterrupt):
        while True:
            asyncio.run(run_benchmark(bench))


async def run_benchmark(bench):
    """Run a benchmark."""
    menuai = core.menuai("")
    runtime = await bench(menuai)
    print(f"Benchmark {bench.__name__} done in {runtime}s")
    await menuai.async_stop()


def benchmark[_CallableT: Callable](func: _CallableT) -> _CallableT:
    """Decorate to mark a benchmark."""
    BENCHMARKS[func.__name__] = func
    return func


@benchmark
async def fire_events(menuai: core.menuai) -> float:
    """Fire a million events."""
    count = 0
    event_name = "benchmark_event"
    events_to_fire = 10**6

    @core.callback
    def listener(_):
        """Handle event."""
        nonlocal count
        count += 1

    menuai.bus.async_listen(event_name, listener)

    for _ in range(events_to_fire):
        menuai.bus.async_fire(event_name)

    start = timer()

    await menuai.async_block_till_done()

    assert count == events_to_fire

    return timer() - start


@benchmark
async def fire_events_with_filter(menuai: core.menuai) -> float:
    """Fire a million events with a filter that rejects them."""
    count = 0
    event_name = "benchmark_event"
    events_to_fire = 10**6

    @core.callback
    def event_filter(event_data):
        """Filter event."""
        return False

    @core.callback
    def listener(_):
        """Handle event."""
        nonlocal count
        count += 1

    menuai.bus.async_listen(event_name, listener, event_filter=event_filter)

    for _ in range(events_to_fire):
        menuai.bus.async_fire(event_name)

    start = timer()

    await menuai.async_block_till_done()

    assert count == 0

    return timer() - start


@benchmark
async def state_changed_helper(menuai: core.menuai) -> float:
    """Run a million events through state changed helper with 1000 entities."""
    count = 0
    entity_id = "light.kitchen"
    event = asyncio.Event()

    @core.callback
    def listener(*args):
        """Handle event."""
        nonlocal count
        count += 1

        if count == 10**6:
            event.set()

    for idx in range(1000):
        async_track_state_change(menuai, f"{entity_id}{idx}", listener, "off", "on")
    event_data = {
        "entity_id": f"{entity_id}0",
        "old_state": core.State(entity_id, "off"),
        "new_state": core.State(entity_id, "on"),
    }

    for _ in range(10**6):
        menuai.bus.async_fire(EVENT_STATE_CHANGED, event_data)  # type: ignore[misc]

    start = timer()

    await event.wait()

    return timer() - start


@benchmark
async def state_changed_event_helper(menuai: core.menuai) -> float:
    """Run a million events through state changed event helper with 1000 entities."""
    count = 0
    entity_id = "light.kitchen"
    events_to_fire = 10**6

    @core.callback
    def listener(*args):
        """Handle event."""
        nonlocal count
        count += 1

    async_track_state_change_event(
        menuai, [f"{entity_id}{idx}" for idx in range(1000)], listener
    )

    event_data = {
        "entity_id": f"{entity_id}0",
        "old_state": core.State(entity_id, "off"),
        "new_state": core.State(entity_id, "on"),
    }

    for _ in range(events_to_fire):
        menuai.bus.async_fire(EVENT_STATE_CHANGED, event_data)  # type: ignore[misc]

    start = timer()

    await menuai.async_block_till_done()

    assert count == events_to_fire

    return timer() - start


@benchmark
async def state_changed_event_filter_helper(menuai: core.menuai) -> float:
    """Run a million events through state changed event helper.

    With 1000 entities that all get filtered.
    """
    count = 0
    entity_id = "light.kitchen"
    events_to_fire = 10**6

    @core.callback
    def listener(*args):
        """Handle event."""
        nonlocal count
        count += 1

    async_track_state_change_event(
        menuai, [f"{entity_id}{idx}" for idx in range(1000)], listener
    )

    event_data = {
        "entity_id": "switch.no_listeners",
        "old_state": core.State(entity_id, "off"),
        "new_state": core.State(entity_id, "on"),
    }

    for _ in range(events_to_fire):
        menuai.bus.async_fire(EVENT_STATE_CHANGED, event_data)  # type: ignore[misc]

    start = timer()

    await menuai.async_block_till_done()

    assert count == 0

    return timer() - start


@benchmark
async def filtering_entity_id(menuai: core.menuai) -> float:
    """Run a 100k state changes through entity filter."""
    config = {
        "include": {
            "domains": [
                "automation",
                "script",
                "group",
                "media_player",
                "custom_component",
            ],
            "entity_globs": [
                "binary_sensor.*_contact",
                "binary_sensor.*_occupancy",
                "binary_sensor.*_detected",
                "binary_sensor.*_active",
                "input_*",
                "device_tracker.*_phone",
                "switch.*_light",
                "binary_sensor.*_charging",
                "binary_sensor.*_lock",
                "binary_sensor.*_connected",
            ],
            "entities": [
                "test.entity_1",
                "test.entity_2",
                "binary_sensor.garage_door_open",
                "test.entity_3",
                "test.entity_4",
            ],
        },
        "exclude": {
            "domains": ["input_number"],
            "entity_globs": ["media_player.google_*", "group.all_*"],
            "entities": [],
        },
    }

    entity_ids = [
        "automation.home_arrival",
        "script.shut_off_house",
        "binary_sensor.garage_door_open",
        "binary_sensor.front_door_lock",
        "binary_sensor.kitchen_motion_sensor_occupancy",
        "switch.desk_lamp",
        "light.dining_room",
        "input_boolean.guest_staying_over",
        "person.eleanor_fant",
        "alert.issue_at_home",
        "calendar.eleanor_fant_s_calendar",
        "sun.sun",
    ]

    entities_filter = convert_include_exclude_filter(config)
    size = len(entity_ids)

    start = timer()

    for i in range(10**5):
        entities_filter(entity_ids[i % size])

    return timer() - start


@benchmark
async def valid_entity_id(menuai: core.menuai) -> float:
    """Run valid entity ID a million times."""
    start = timer()
    for _ in range(10**6):
        core.valid_entity_id("light.kitchen")
    return timer() - start


@benchmark
async def json_serialize_states(menuai: core.menuai) -> float:
    """Serialize million states with websocket default encoder."""
    states = [
        core.State("light.kitchen", "on", {"friendly_name": "Kitchen Lights"})
        for _ in range(10**6)
    ]

    start = timer()
    JSON_DUMP(states)
    return timer() - start
