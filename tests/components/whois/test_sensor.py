"""Tests for the sensors provided by the Whois integration."""

from unittest.mock import MagicMock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.whois.const import SCAN_INTERVAL
from menuai.const import STATE_UNKNOWN
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed

pytestmark = [
    pytest.mark.usefixtures("init_integration"),
    pytest.mark.freeze_time("2022-01-01 12:00:00", tz_offset=0),
]


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    "entity_id",
    [
        "sensor.home_assistant_io_admin",
        "sensor.home_assistant_io_created",
        "sensor.home_assistant_io_days_until_expiration",
        "sensor.home_assistant_io_expires",
        "sensor.home_assistant_io_last_updated",
        "sensor.home_assistant_io_owner",
        "sensor.home_assistant_io_registrant",
        "sensor.home_assistant_io_registrar",
        "sensor.home_assistant_io_reseller",
        "sensor.home_assistant_io_status",
    ],
)
async def test_whois_sensors(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    entity_id: str,
) -> None:
    """Test the Whois sensors."""

    assert (state := menuai.states.get(entity_id))
    assert state == snapshot

    assert (entity_entry := entity_registry.async_get(entity_id))
    assert entity_entry == snapshot

    assert entity_entry.device_id
    assert (device_entry := device_registry.async_get(entity_entry.device_id))
    assert device_entry == snapshot


async def test_whois_sensors_missing_some_attrs(
    menuai: menuai, entity_registry: er.EntityRegistry, snapshot: SnapshotAssertion
) -> None:
    """Test the Whois sensors with owner and reseller missing."""
    assert (state := menuai.states.get("sensor.home_assistant_io_last_updated"))
    assert state == snapshot

    assert (entry := entity_registry.async_get("sensor.home_assistant_io_last_updated"))
    assert entry == snapshot


@pytest.mark.parametrize(
    "entity_id",
    [
        "sensor.home_assistant_io_admin",
        "sensor.home_assistant_io_owner",
        "sensor.home_assistant_io_registrant",
        "sensor.home_assistant_io_registrar",
        "sensor.home_assistant_io_reseller",
        "sensor.home_assistant_io_status",
    ],
)
async def test_disabled_by_default_sensors(
    menuai: menuai, entity_id: str, entity_registry: er.EntityRegistry
) -> None:
    """Test the disabled by default Whois sensors."""
    assert menuai.states.get(entity_id) is None
    assert (entry := entity_registry.async_get(entity_id))
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    "entity_id",
    [
        "sensor.home_assistant_io_admin",
        "sensor.home_assistant_io_created",
        "sensor.home_assistant_io_days_until_expiration",
        "sensor.home_assistant_io_expires",
        "sensor.home_assistant_io_last_updated",
        "sensor.home_assistant_io_owner",
        "sensor.home_assistant_io_registrant",
        "sensor.home_assistant_io_registrar",
        "sensor.home_assistant_io_reseller",
        "sensor.home_assistant_io_status",
    ],
)
async def test_no_data(
    menuai: menuai, mock_whois: MagicMock, entity_id: str
) -> None:
    """Test whois sensors become unknown when there is no data provided."""
    mock_whois.return_value = None

    async_fire_time_changed(menuai, dt_util.utcnow() + SCAN_INTERVAL)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNKNOWN
