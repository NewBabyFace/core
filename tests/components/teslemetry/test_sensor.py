"""Test the Teslemetry sensor platform."""

from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion
from teslemetry_stream import Signal

from menuai.components.teslemetry.coordinator import VEHICLE_INTERVAL
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import assert_entities, assert_entities_alt, setup_platform
from .const import VEHICLE_DATA_ALT

from tests.common import async_fire_time_changed


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    mock_vehicle_data: AsyncMock,
) -> None:
    """Tests that the sensor entities with the legacy polling are correct."""

    freezer.move_to("2024-01-01 00:00:00+00:00")

    # Force the vehicle to use polling
    with patch("tesla_fleet_api.teslemetry.Vehicle.pre2021", return_value=True):
        entry = await setup_platform(menuai, [Platform.SENSOR])

    assert_entities(menuai, entry.entry_id, entity_registry, snapshot)

    # Coordinator refresh
    mock_vehicle_data.return_value = VEHICLE_DATA_ALT
    freezer.tick(VEHICLE_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert_entities_alt(menuai, entry.entry_id, entity_registry, snapshot)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors_streaming(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    mock_vehicle_data: AsyncMock,
    mock_add_listener: AsyncMock,
) -> None:
    """Tests that the sensor entities with streaming are correct."""

    freezer.move_to("2024-01-01 00:00:00+00:00")

    entry = await setup_platform(menuai, [Platform.SENSOR])

    # Stream update
    mock_add_listener.send(
        {
            "vin": VEHICLE_DATA_ALT["response"]["vin"],
            "data": {
                Signal.DETAILED_CHARGE_STATE: "DetailedChargeStateCharging",
                Signal.BATTERY_LEVEL: 90,
                Signal.AC_CHARGING_ENERGY_IN: 10,
                Signal.AC_CHARGING_POWER: 2,
                Signal.CHARGING_CABLE_TYPE: None,
                Signal.TIME_TO_FULL_CHARGE: 0.166666667,
                Signal.MINUTES_TO_ARRIVAL: None,
            },
            "credits": {
                "type": "wake_up",
                "cost": 20,
                "name": "wake_up",
                "balance": 1980,
            },
            "createdAt": "2024-10-04T10:45:17.537Z",
        }
    )
    await menuai.async_block_till_done()

    # Reload the entry
    await menuai.config_entries.async_reload(entry.entry_id)
    await menuai.async_block_till_done()

    # Assert the entities restored their values
    for entity_id in (
        "sensor.test_charging",
        "sensor.test_battery_level",
        "sensor.test_charge_energy_added",
        "sensor.test_charger_power",
        "sensor.test_charge_cable",
        "sensor.test_time_to_full_charge",
        "sensor.test_time_to_arrival",
        "sensor.teslemetry_credits",
    ):
        state = menuai.states.get(entity_id)
        assert state.state == snapshot(name=f"{entity_id}-state")
