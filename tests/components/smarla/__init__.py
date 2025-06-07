"""Tests for the Smarla integration."""

from typing import Any
from unittest.mock import AsyncMock

from menuai.core import menuai

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> bool:
    """Set up the component."""
    config_entry.add_to_menuai(menuai)
    if success := await menuai.config_entries.async_setup(config_entry.entry_id):
        await menuai.async_block_till_done()
    return success


async def update_property_listeners(mock: AsyncMock, value: Any = None) -> None:
    """Update the property listeners for the mock object."""
    for call in mock.add_listener.call_args_list:
        await call[0][0](value)
