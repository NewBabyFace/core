"""Test the Smart Meter Texas module."""

from unittest.mock import patch

from menuai.components.menuai import (
    DOMAIN as HA_DOMAIN,
    SERVICE_UPDATE_ENTITY,
)
from menuai.components.smart_meter_texas.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai
from menuai.setup import async_setup_component

from .conftest import TEST_ENTITY_ID, setup_integration

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_setup_with_no_config(menuai: menuai) -> None:
    """Test that no config is successful."""
    assert await async_setup_component(menuai, DOMAIN, {}) is True
    await menuai.async_block_till_done()

    # Assert no flows were started.
    assert len(menuai.config_entries.flow.async_progress()) == 0


async def test_auth_failure(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test if user's username or password is not accepted."""
    await setup_integration(menuai, config_entry, aioclient_mock, auth_fail=True)

    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_api_timeout(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that a timeout results in ConfigEntryNotReady."""
    await setup_integration(menuai, config_entry, aioclient_mock, auth_timeout=True)

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_update_failure(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the coordinator handles a bad response."""
    await setup_integration(menuai, config_entry, aioclient_mock, bad_reading=True)
    await async_setup_component(menuai, HA_DOMAIN, {})
    await menuai.async_block_till_done()
    with patch("smart_meter_texas.Meter.read_meter") as updater:
        await menuai.services.async_call(
            HA_DOMAIN,
            SERVICE_UPDATE_ENTITY,
            {ATTR_ENTITY_ID: TEST_ENTITY_ID},
            blocking=True,
        )
        await menuai.async_block_till_done()
        updater.assert_called_once()


async def test_unload_config_entry(
    menuai: menuai, config_entry, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test entry unloading."""
    await setup_integration(menuai, config_entry, aioclient_mock)

    config_entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(config_entries) == 1
    assert config_entries[0] is config_entry
    assert config_entry.state is ConfigEntryState.LOADED

    await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.NOT_LOADED
