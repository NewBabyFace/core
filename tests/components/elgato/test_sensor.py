"""Tests for the Elgato sensor platform."""

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

pytestmark = [
    pytest.mark.parametrize("device_fixtures", ["key-light-mini"]),
    pytest.mark.usefixtures("device_fixtures", "init_integration", "mock_elgato"),
]


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    "entity_id",
    [
        "sensor.frenck_battery",
        "sensor.frenck_battery_voltage",
        "sensor.frenck_charging_current",
        "sensor.frenck_charging_power",
        "sensor.frenck_charging_voltage",
    ],
)
async def test_sensors(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    entity_id: str,
) -> None:
    """Test the Elgato sensors."""

    assert (state := menuai.states.get(entity_id))
    assert state == snapshot

    assert (entry := entity_registry.async_get(entity_id))
    assert entry == snapshot

    assert entry.device_id
    assert (device_entry := device_registry.async_get(entry.device_id))
    assert device_entry == snapshot


@pytest.mark.parametrize(
    "entity_id",
    [
        "sensor.frenck_battery_voltage",
        "sensor.frenck_charging_current",
        "sensor.frenck_charging_power",
        "sensor.frenck_charging_voltage",
    ],
)
async def test_disabled_by_default_sensors(
    menuai: menuai, entity_registry: er.EntityRegistry, entity_id: str
) -> None:
    """Test the disabled by default Elgato sensors."""
    assert not menuai.states.get(entity_id)

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
