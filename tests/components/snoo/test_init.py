"""Test init for Snoo."""

from unittest.mock import AsyncMock

from python_snoo.exceptions import SnooAuthException

from menuai.components.snoo import SnooDeviceError
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from . import async_init_integration


async def test_async_setup_entry(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test a successful setup entry."""
    entry = await async_init_integration(menuai)
    assert len(menuai.states.async_all("sensor")) == 2
    assert entry.state == ConfigEntryState.LOADED


async def test_cannot_auth(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test that we are put into retry when we fail to auth."""
    bypass_api.authorize.side_effect = SnooAuthException
    entry = await async_init_integration(menuai)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_failed_devices(menuai: menuai, bypass_api: AsyncMock) -> None:
    """Test that we are put into retry when we fail to get devices."""
    bypass_api.get_devices.side_effect = SnooDeviceError
    entry = await async_init_integration(menuai)
    assert entry.state is ConfigEntryState.SETUP_RETRY
