"""Test the Met integration init."""

import pytest

from menuai.components.met.const import (
    DEFAULT_HOME_LATITUDE,
    DEFAULT_HOME_LONGITUDE,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai
from menuai.core_config import async_process_ha_core_config
from menuai.helpers import device_registry as dr

from . import init_integration


async def test_unload_entry(menuai: menuai) -> None:
    """Test successful unload of entry."""
    entry = await init_integration(menuai)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.LOADED

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert not menuai.data.get(DOMAIN)


async def test_fail_default_home_entry(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test abort setup of default home location."""
    await async_process_ha_core_config(
        menuai,
        {"latitude": 52.3731339, "longitude": 4.8903147},
    )

    assert menuai.config.latitude == DEFAULT_HOME_LATITUDE
    assert menuai.config.longitude == DEFAULT_HOME_LONGITUDE

    entry = await init_integration(menuai, track_home=True)

    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1
    assert entry.state is ConfigEntryState.SETUP_ERROR

    assert (
        "Skip setting up met.no integration; No Home location has been set"
        in caplog.text
    )


async def test_removing_incorrect_devices(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    caplog: pytest.LogCaptureFixture,
    mock_weather,
) -> None:
    """Test we remove incorrect devices."""
    entry = await init_integration(menuai)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        name="Forecast_legacy",
        entry_type=dr.DeviceEntryType.SERVICE,
        identifiers={(DOMAIN,)},
        manufacturer="Met.no",
        model="Forecast",
        configuration_url="https://www.met.no/en",
    )

    assert await menuai.config_entries.async_reload(entry.entry_id)
    assert len(menuai.config_entries.async_entries(DOMAIN)) == 1

    assert not device_registry.async_get_device(identifiers={(DOMAIN,)})
    assert device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert "Removing improper device Forecast_legacy" in caplog.text
