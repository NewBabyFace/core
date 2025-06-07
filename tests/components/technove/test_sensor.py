"""Tests for the TechnoVE sensor platform."""

from datetime import timedelta
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from technove import Station, Status, TechnoVEError

from menuai.components.technove.const import DOMAIN
from menuai.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_with_selected_platforms

from tests.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_load_json_object_fixture,
)


@pytest.mark.usefixtures("entity_registry_enabled_by_default", "mock_technove")
async def test_sensors(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the creation and values of the TechnoVE sensors."""
    await setup_with_selected_platforms(menuai, mock_config_entry, [Platform.SENSOR])
    entity_entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )

    assert entity_entries
    for entity_entry in entity_entries:
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert menuai.states.get(entity_entry.entity_id) == snapshot(
            name=f"{entity_entry.entity_id}-state"
        )


@pytest.mark.parametrize(
    "entity_id",
    [
        "sensor.technove_station_signal_strength",
        "sensor.technove_station_wi_fi_network_name",
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_disabled_by_default_sensors(
    menuai: menuai, entity_registry: er.EntityRegistry, entity_id: str
) -> None:
    """Test the disabled by default TechnoVE sensors."""
    assert menuai.states.get(entity_id) is None

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_no_wifi_support(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_technove: MagicMock,
) -> None:
    """Test missing Wi-Fi information from TechnoVE device."""
    # Remove Wi-Fi info
    device = mock_technove.update.return_value
    device.info.network_ssid = None

    # Setup
    mock_config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get("sensor.technove_station_wi_fi_network_name"))
    assert state.state == STATE_UNKNOWN


@pytest.mark.usefixtures("init_integration")
async def test_sensor_update_failure(
    menuai: menuai,
    mock_technove: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test coordinator update failure."""
    entity_id = "sensor.technove_station_status"

    assert menuai.states.get(entity_id).state == Status.PLUGGED_CHARGING.value

    mock_technove.update.side_effect = TechnoVEError("Test error")
    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("init_integration")
async def test_sensor_unknown_status(
    menuai: menuai,
    mock_technove: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test coordinator update failure."""
    entity_id = "sensor.technove_station_status"

    assert menuai.states.get(entity_id).state == Status.PLUGGED_CHARGING.value

    mock_technove.update.return_value = Station(
        await async_load_json_object_fixture(menuai, "station_bad_status.json", DOMAIN)
    )

    freezer.tick(timedelta(minutes=5, seconds=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get(entity_id).state == STATE_UNKNOWN
    # Other sensors should still be available
    assert menuai.states.get("sensor.technove_station_total_energy_usage").state == "1234"
