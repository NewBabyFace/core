"""Test honeywell setup process."""

from unittest.mock import MagicMock, create_autospec, patch

from aiohttp.client_exceptions import ClientConnectionError
import aiosomecomfort
import pytest

from menuai.components.honeywell.const import (
    CONF_COOL_AWAY_TEMPERATURE,
    CONF_HEAT_AWAY_TEMPERATURE,
    DOMAIN,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import CONF_PASSWORD, CONF_USERNAME
from menuai.core import menuai
from menuai.helpers import device_registry as dr

from . import init_integration

from tests.common import MockConfigEntry

MIGRATE_OPTIONS_KEYS = {CONF_COOL_AWAY_TEMPERATURE, CONF_HEAT_AWAY_TEMPERATURE}


@patch("menuai.components.honeywell.UPDATE_LOOP_SLEEP_TIME", 0)
async def test_setup_entry(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Initialize the config entry."""
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert (
        menuai.states.async_entity_ids_count() == 4
    )  # 1 climate entity; 2 sensor entities


@patch("menuai.components.honeywell.UPDATE_LOOP_SLEEP_TIME", 0)
async def test_setup_multiple_entry(
    menuai: menuai, config_entry: MockConfigEntry, config_entry2: MockConfigEntry
) -> None:
    """Initialize the config entry."""
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    config_entry2.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry2.entry_id)
    await menuai.async_block_till_done()
    assert config_entry2.state is ConfigEntryState.LOADED


async def test_setup_multiple_thermostats(
    menuai: menuai,
    config_entry: MockConfigEntry,
    location: MagicMock,
    another_device: MagicMock,
) -> None:
    """Test that the config form is shown."""
    location.devices_by_id[another_device.deviceid] = another_device
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert (
        menuai.states.async_entity_ids_count() == 8
    )  # 2 climate entities; 4 sensor entities; 2 switch entities


async def test_setup_multiple_thermostats_with_same_deviceid(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    config_entry: MockConfigEntry,
    device: MagicMock,
    client: MagicMock,
) -> None:
    """Test Honeywell TCC API returning duplicate device IDs."""
    mock_location2 = create_autospec(aiosomecomfort.Location, instance=True)
    mock_location2.locationid.return_value = "location2"
    mock_location2.devices_by_id = {device.deviceid: device}
    client.locations_by_id["location2"] = mock_location2
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert (
        menuai.states.async_entity_ids_count() == 4
    )  # 1 climate entity; 2 sensor entities; 1 switch enitiy
    assert "Platform honeywell does not generate unique IDs" not in caplog.text


async def test_away_temps_migration(menuai: menuai) -> None:
    """Test away temps migrate to config options."""
    legacy_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_USERNAME: "fake",
            CONF_PASSWORD: "user",
            CONF_COOL_AWAY_TEMPERATURE: 1,
            CONF_HEAT_AWAY_TEMPERATURE: 2,
        },
        options={},
    )

    legacy_config.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(legacy_config.entry_id)
    await menuai.async_block_till_done()
    assert legacy_config.options == {
        CONF_COOL_AWAY_TEMPERATURE: 1,
        CONF_HEAT_AWAY_TEMPERATURE: 2,
    }


async def test_login_error(
    menuai: menuai, client: MagicMock, config_entry: MagicMock
) -> None:
    """Test login errors from API."""
    client.login.side_effect = aiosomecomfort.AuthError
    await init_integration(menuai, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_ERROR


@pytest.mark.parametrize(
    "the_error",
    [
        aiosomecomfort.ConnectionError,
        aiosomecomfort.device.ConnectionTimeout,
        aiosomecomfort.device.SomeComfortError,
        ClientConnectionError,
    ],
)
async def test_connection_error(
    menuai: menuai,
    client: MagicMock,
    config_entry: MagicMock,
    the_error: Exception,
) -> None:
    """Test Connection errors from API."""
    client.login.side_effect = the_error
    await init_integration(menuai, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_no_devices(
    menuai: menuai, client: MagicMock, config_entry: MagicMock
) -> None:
    """Test no devices from API."""
    client.locations_by_id = {}
    await init_integration(menuai, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_remove_stale_device(
    menuai: menuai,
    config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
    location: MagicMock,
    another_device: MagicMock,
    client: MagicMock,
) -> None:
    """Test that the stale device is removed."""
    location.devices_by_id[another_device.deviceid] = another_device

    config_entry_other = MockConfigEntry(
        domain="OtherDomain",
        data={},
        unique_id="unique_id",
    )
    config_entry_other.add_to_menuai(menuai)
    device_entry_other = device_registry.async_get_or_create(
        config_entry_id=config_entry_other.entry_id,
        identifiers={("OtherDomain", 7654321)},
    )

    config_entry.add_to_menuai(menuai)
    device_registry.async_update_device(
        device_entry_other.id,
        add_config_entry_id=config_entry.entry_id,
        merge_identifiers={(DOMAIN, 7654321)},
    )

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    assert menuai.states.async_entity_ids_count() == 8

    device_entries = dr.async_entries_for_config_entry(
        device_registry, config_entry.entry_id
    )

    device_entries_other = dr.async_entries_for_config_entry(
        device_registry, config_entry_other.entry_id
    )

    assert len(device_entries) == 2
    assert any((DOMAIN, 1234567) in device.identifiers for device in device_entries)
    assert any((DOMAIN, 7654321) in device.identifiers for device in device_entries)
    assert any(
        ("OtherDomain", 7654321) in device.identifiers for device in device_entries
    )
    assert len(device_entries_other) == 1
    assert any(
        ("OtherDomain", 7654321) in device.identifiers
        for device in device_entries_other
    )
    assert any(
        (DOMAIN, 7654321) in device.identifiers for device in device_entries_other
    )

    assert await menuai.config_entries.async_unload(config_entry.entry_id)
    await menuai.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED

    del location.devices_by_id[another_device.deviceid]

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    await menuai.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED

    assert (
        menuai.states.async_entity_ids_count() == 4
    )  # 1 climate entities; 2 sensor entities; 1 switch entity

    device_entries = dr.async_entries_for_config_entry(
        device_registry, config_entry.entry_id
    )
    assert len(device_entries) == 1
    assert any((DOMAIN, 1234567) in device.identifiers for device in device_entries)
    assert not any((DOMAIN, 7654321) in device.identifiers for device in device_entries)
    assert not any(
        ("OtherDomain", 7654321) in device.identifiers for device in device_entries
    )

    device_entries_other = dr.async_entries_for_config_entry(
        device_registry, config_entry_other.entry_id
    )
    assert len(device_entries_other) == 1
    assert any(
        ("OtherDomain", 7654321) in device.identifiers
        for device in device_entries_other
    )
