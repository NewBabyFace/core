"""Test Slack integration."""

from menuai.components.slack.const import DOMAIN
from menuai.config_entries import ConfigEntry, ConfigEntryState
from menuai.core import menuai

from . import CONF_DATA, async_init_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_setup(menuai: menuai, aioclient_mock: AiohttpClientMocker) -> None:
    """Test Slack setup."""
    entry: ConfigEntry = await async_init_integration(menuai, aioclient_mock)
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.data == CONF_DATA


async def test_async_setup_entry_not_ready(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that it throws ConfigEntryNotReady when exception occurs during setup."""
    entry: ConfigEntry = await async_init_integration(
        menuai, aioclient_mock, error="cannot_connect"
    )
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_async_setup_entry_invalid_auth(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test invalid auth during setup."""
    entry: ConfigEntry = await async_init_integration(
        menuai, aioclient_mock, error="invalid_auth"
    )
    await menuai.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
