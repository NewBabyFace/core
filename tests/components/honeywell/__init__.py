"""Tests for Honeywell component."""

from unittest.mock import MagicMock

from menuai.core import menuai

from tests.common import MockConfigEntry


async def init_integration(
    menuai: menuai, entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the Honeywell integration in MenuAI."""
    entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    return entry


def reset_mock(device: MagicMock) -> None:
    """Reset the mocks for test."""
    device.set_setpoint_cool.reset_mock()
    device.set_setpoint_heat.reset_mock()
    device.set_hold_heat.reset_mock()
    device.set_hold_cool.reset_mock()
