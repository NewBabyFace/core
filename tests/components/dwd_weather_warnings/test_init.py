"""Tests for Deutscher Wetterdienst (DWD) Weather Warnings integration."""

from unittest.mock import MagicMock

from menuai.components.dwd_weather_warnings.const import (
    CONF_REGION_DEVICE_TRACKER,
    DOMAIN,
)
from menuai.components.dwd_weather_warnings.coordinator import (
    DwdWeatherWarningsCoordinator,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_LATITUDE, ATTR_LONGITUDE, STATE_HOME
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.helpers.device_registry import DeviceEntryType

from . import init_integration

from tests.common import MockConfigEntry


async def test_load_unload_entry(
    menuai: menuai,
    mock_identifier_entry: MockConfigEntry,
    mock_dwdwfsapi: MagicMock,
) -> None:
    """Test loading and unloading the integration with a region identifier based entry."""
    entry = await init_integration(menuai, mock_identifier_entry)

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, DwdWeatherWarningsCoordinator)

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_removing_old_device(
    menuai: menuai,
    mock_identifier_entry: MockConfigEntry,
    mock_dwdwfsapi: MagicMock,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test removing old device when reloading the integration."""

    mock_identifier_entry.add_to_menuai(menuai)

    device_registry.async_get_or_create(
        identifiers={(DOMAIN, mock_identifier_entry.entry_id)},
        config_entry_id=mock_identifier_entry.entry_id,
        entry_type=DeviceEntryType.SERVICE,
        name="test",
    )

    assert (
        device_registry.async_get_device(
            identifiers={(DOMAIN, mock_identifier_entry.entry_id)}
        )
        is not None
    )

    await menuai.config_entries.async_setup(mock_identifier_entry.entry_id)
    await menuai.async_block_till_done()

    assert (
        device_registry.async_get_device(
            identifiers={(DOMAIN, mock_identifier_entry.entry_id)}
        )
        is None
    )


async def test_load_invalid_registry_entry(
    menuai: menuai, mock_tracker_entry: MockConfigEntry
) -> None:
    """Test loading the integration with an invalid registry entry ID."""
    INVALID_DATA = mock_tracker_entry.data.copy()
    INVALID_DATA[CONF_REGION_DEVICE_TRACKER] = "invalid_registry_id"

    entry = await init_integration(
        menuai, MockConfigEntry(domain=DOMAIN, data=INVALID_DATA)
    )
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_load_missing_device_tracker(
    menuai: menuai, mock_tracker_entry: MockConfigEntry
) -> None:
    """Test loading the integration with a missing device tracker."""
    entry = await init_integration(menuai, mock_tracker_entry)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_load_missing_required_attribute(
    menuai: menuai, mock_tracker_entry: MockConfigEntry
) -> None:
    """Test loading the integration with a device tracker missing a required attribute."""
    mock_tracker_entry.add_to_menuai(menuai)
    menuai.states.async_set(
        mock_tracker_entry.data[CONF_REGION_DEVICE_TRACKER],
        STATE_HOME,
        {ATTR_LONGITUDE: "7.610263"},
    )

    await menuai.config_entries.async_setup(mock_tracker_entry.entry_id)
    await menuai.async_block_till_done()
    assert mock_tracker_entry.state is ConfigEntryState.SETUP_RETRY


async def test_load_valid_device_tracker(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_tracker_entry: MockConfigEntry,
    mock_dwdwfsapi: MagicMock,
) -> None:
    """Test loading the integration with a valid device tracker based entry."""
    mock_tracker_entry.add_to_menuai(menuai)
    entity_registry.async_get_or_create(
        "device_tracker",
        mock_tracker_entry.domain,
        "uuid",
        suggested_object_id="test_gps",
        config_entry=mock_tracker_entry,
    )

    menuai.states.async_set(
        mock_tracker_entry.data[CONF_REGION_DEVICE_TRACKER],
        STATE_HOME,
        {ATTR_LATITUDE: "50.180454", ATTR_LONGITUDE: "7.610263"},
    )

    await menuai.config_entries.async_setup(mock_tracker_entry.entry_id)
    await menuai.async_block_till_done()

    assert mock_tracker_entry.state is ConfigEntryState.LOADED
    assert isinstance(mock_tracker_entry.runtime_data, DwdWeatherWarningsCoordinator)
