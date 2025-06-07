"""Ecovacs test util."""

import asyncio

from deebot_client.event_bus import EventBus
from deebot_client.events import Event

from menuai.core import menuai


async def block_till_done(menuai: menuai, event_bus: EventBus) -> None:
    """Block till done."""
    await asyncio.gather(*event_bus._tasks)
    await menuai.async_block_till_done()


async def notify_and_wait(
    menuai: menuai, event_bus: EventBus, event: Event
) -> None:
    """Block till done."""
    event_bus.notify(event)
    await block_till_done(menuai, event_bus)
