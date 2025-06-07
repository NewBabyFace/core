"""Tests for the Miele integration."""

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


def get_data_callback(mock: AsyncMock) -> Callable[[int], Awaitable[None]]:
    """Get registered callback for api data push."""
    return mock.listen_events.call_args_list[0].kwargs.get("data_callback")


def get_actions_callback(mock: AsyncMock) -> Callable[[int], Awaitable[None]]:
    """Get registered callback for api data push."""
    return mock.listen_events.call_args_list[0].kwargs.get("actions_callback")
