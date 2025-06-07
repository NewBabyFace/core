"""Tests for the Bosch Alarm component."""

from unittest.mock import AsyncMock

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


async def call_observable(menuai: menuai, observable: AsyncMock) -> None:
    """Call the observable with the given event."""
    for callback in observable.attach.call_args_list:
        callback[0][0]()
    await menuai.async_block_till_done()
