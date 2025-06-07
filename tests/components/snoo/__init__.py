"""Tests for the Happiest Baby Snoo integration."""

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from python_snoo.containers import SnooData

from menuai.components.snoo.const import DOMAIN
from menuai.config_entries import ConfigEntry
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from tests.common import MockConfigEntry


def create_entry(
    menuai: menuai,
) -> ConfigEntry:
    """Add config entry in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="test-username",
        data={
            CONF_USERNAME: "test-username",
            CONF_PASSWORD: "sample",
        },
        # This is also gotten from the fake jwt
        unique_id="123e4567-e89b-12d3-a456-426614174000",
        version=1,
    )
    entry.add_to_menuai(menuai)
    return entry


async def async_init_integration(menuai: menuai) -> ConfigEntry:
    """Set up the Snoo integration in MenuAI."""

    entry = create_entry(menuai)

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry


def find_update_callback(
    mock: AsyncMock, serial_number: str
) -> Callable[[SnooData], Awaitable[None]]:
    """Find the update callback for a specific identifier."""
    for call in mock.subscribe.call_args_list:
        if call[0][0].serialNumber == serial_number:
            return call[0][1]
    pytest.fail(f"Callback for identifier {serial_number} not found")
