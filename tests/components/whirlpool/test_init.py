"""Test the Whirlpool Sixth Sense init."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
from whirlpool.auth import AccountLockedError
from whirlpool.backendselector import Brand, Region

from menuai.components.whirlpool.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_PASSWORD, CONF_REGION, CONF_USERNAME
from menuai.core import menuai

from . import init_integration, init_integration_with_entry

from tests.common import MockConfigEntry


async def test_setup(
    menuai: menuai,
    mock_backend_selector_api: MagicMock,
    region,
    brand,
) -> None:
    """Test setup."""
    entry = await init_integration(menuai, region[0], brand[0])
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED
    mock_backend_selector_api.assert_called_once_with(brand[1], region[1])


async def test_setup_region_fallback(
    menuai: menuai,
    mock_backend_selector_api: MagicMock,
) -> None:
    """Test setup when no region is available on the ConfigEntry.

    This can happen after a version update, since there was no region in the first versions.
    """

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "nobody",
            CONF_PASSWORD: "qwerty",
        },
    )
    entry = await init_integration_with_entry(menuai, entry)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED
    mock_backend_selector_api.assert_called_once_with(Brand.Whirlpool, Region.EU)


async def test_setup_brand_fallback(
    menuai: menuai,
    region,
    mock_backend_selector_api: MagicMock,
) -> None:
    """Test setup when no brand is available on the ConfigEntry.

    This can happen after a version update, since the brand was not selected or stored in the earlier versions.
    """

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "nobody",
            CONF_PASSWORD: "qwerty",
            CONF_REGION: region[0],
        },
    )
    entry = await init_integration_with_entry(menuai, entry)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED
    mock_backend_selector_api.assert_called_once_with(Brand.Whirlpool, region[1])


async def test_setup_no_appliances(
    menuai: menuai, mock_appliances_manager_api: MagicMock
) -> None:
    """Test setup when there are no appliances available."""
    mock_appliances_manager_api.return_value.aircons = []
    mock_appliances_manager_api.return_value.washer_dryers = []
    await init_integration(menuai)
    assert len(menuai.states.async_all()) == 0


async def test_setup_http_exception(
    menuai: menuai,
    mock_auth_api: MagicMock,
) -> None:
    """Test setup with an http exception."""
    mock_auth_api.return_value.do_auth = AsyncMock(
        side_effect=aiohttp.ClientConnectionError()
    )
    entry = await init_integration(menuai)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_auth_failed(
    menuai: menuai,
    mock_auth_api: MagicMock,
) -> None:
    """Test setup with failed auth."""
    mock_auth_api.return_value.do_auth = AsyncMock()
    mock_auth_api.return_value.is_access_token_valid.return_value = False
    entry = await init_integration(menuai)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_auth_account_locked(
    menuai: menuai,
    mock_auth_api: MagicMock,
) -> None:
    """Test setup with failed auth due to account being locked."""
    mock_auth_api.return_value.do_auth.side_effect = AccountLockedError
    entry = await init_integration(menuai)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_fetch_appliances_failed(
    menuai: menuai,
    mock_appliances_manager_api: MagicMock,
) -> None:
    """Test setup with failed fetch_appliances."""
    mock_appliances_manager_api.return_value.fetch_appliances.return_value = False
    entry = await init_integration(menuai)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)
