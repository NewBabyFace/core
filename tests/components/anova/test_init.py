"""Test init for Anova."""

from unittest.mock import patch

from anova_wifi import AnovaApi

from menuai.components.anova.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_DEVICES, CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai

from . import async_init_integration, create_entry

from tests.common import MockConfigEntry


async def test_async_setup_entry(menuai: menuai, anova_api: AnovaApi) -> None:
    """Test a successful setup entry."""
    await async_init_integration(menuai)
    state = menuai.states.get("sensor.anova_precision_cooker_mode")
    assert state is not None
    assert state.state == "idle"


async def test_wrong_login(
    menuai: menuai, anova_api_wrong_login: AnovaApi
) -> None:
    """Test for setup failure if connection to Anova is missing."""
    entry = create_entry(menuai)
    await menuai.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_entry(menuai: menuai, anova_api: AnovaApi) -> None:
    """Test successful unload of entry."""
    entry = await async_init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_no_devices_found(
    menuai: menuai,
    anova_api_no_devices: AnovaApi,
) -> None:
    """Test when there don't seem to be any devices on the account."""
    entry = await async_init_integration(menuai)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_websocket_failure(
    menuai: menuai,
    anova_api_websocket_failure: AnovaApi,
) -> None:
    """Test that we successfully handle a websocket failure on setup."""
    entry = await async_init_integration(menuai)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_migration_removing_devices_in_config_entry(
    menuai: menuai, anova_api: AnovaApi
) -> None:
    """Test a successful setup entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Anova",
        data={
            CONF_USERNAME: "sample@gmail.com",
            CONF_PASSWORD: "sample",
            CONF_DEVICES: [],
        },
        unique_id="sample@gmail.com",
        version=1,
        minor_version=1,
    )
    entry.add_to_menuai(menuai)

    with patch("menuai.components.anova.AnovaApi.authenticate"):
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.anova_precision_cooker_mode")
    assert state is not None
    assert state.state == "idle"

    assert entry.version == 1
    assert entry.minor_version == 2
    assert CONF_DEVICES not in entry.data
