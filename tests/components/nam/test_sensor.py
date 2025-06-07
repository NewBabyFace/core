"""Test sensor of Nettigo Air Monitor integration."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

from freezegun.api import FrozenDateTimeFactory
from nettigo_air_monitor import ApiError
import pytest
from syrupy.assertion import SnapshotAssertion
from tenacity import RetryError

from menuai.components.nam.const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    Platform,
    UnitOfTemperature,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util.dt import utcnow

from . import INCOMPLETE_NAM_DATA, init_integration

from tests.common import (
    async_fire_time_changed,
    async_load_json_object_fixture,
    snapshot_platform,
)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test states of the air_quality."""
    await menuai.config.async_set_time_zone("UTC")
    freezer.move_to("2024-04-20 12:00:00+00:00")

    with patch("menuai.components.nam.PLATFORMS", [Platform.SENSOR]):
        entry = await init_integration(menuai)

    await snapshot_platform(menuai, entity_registry, snapshot, entry.entry_id)


async def test_sensor_disabled(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test sensor disabled by default."""
    await init_integration(menuai)

    entry = entity_registry.async_get("sensor.nettigo_air_monitor_signal_strength")
    assert entry
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff-signal"
    assert entry.disabled
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    # Test enabling entity
    updated_entry = entity_registry.async_update_entity(
        entry.entity_id, disabled_by=None
    )

    assert updated_entry != entry
    assert updated_entry.disabled is False


async def test_incompleta_data_after_device_restart(menuai: menuai) -> None:
    """Test states of the air_quality after device restart."""
    await init_integration(menuai)

    state = menuai.states.get("sensor.nettigo_air_monitor_heca_temperature")
    assert state
    assert state.state == "7.95"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.TEMPERATURE
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == UnitOfTemperature.CELSIUS

    future = utcnow() + timedelta(minutes=6)
    update_response = Mock(json=AsyncMock(return_value=INCOMPLETE_NAM_DATA))
    with (
        patch("menuai.components.nam.NettigoAirMonitor.initialize"),
        patch(
            "menuai.components.nam.NettigoAirMonitor._async_http_request",
            return_value=update_response,
        ),
    ):
        async_fire_time_changed(menuai, future)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.nettigo_air_monitor_heca_temperature")
    assert state
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("exc", [ApiError("API Error"), RetryError])
async def test_availability(
    menuai: menuai, freezer: FrozenDateTimeFactory, exc: Exception
) -> None:
    """Ensure that we mark the entities unavailable correctly when device causes an error."""
    nam_data = await async_load_json_object_fixture(menuai, "nam_data.json", DOMAIN)

    await init_integration(menuai)

    state = menuai.states.get("sensor.nettigo_air_monitor_bme280_temperature")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "7.56"

    with (
        patch("menuai.components.nam.NettigoAirMonitor.initialize"),
        patch(
            "menuai.components.nam.NettigoAirMonitor._async_http_request",
            side_effect=exc,
        ),
    ):
        freezer.tick(DEFAULT_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.nettigo_air_monitor_bme280_temperature")
    assert state
    assert state.state == STATE_UNAVAILABLE

    update_response = Mock(json=AsyncMock(return_value=nam_data))
    with (
        patch("menuai.components.nam.NettigoAirMonitor.initialize"),
        patch(
            "menuai.components.nam.NettigoAirMonitor._async_http_request",
            return_value=update_response,
        ),
    ):
        freezer.tick(DEFAULT_UPDATE_INTERVAL)
        async_fire_time_changed(menuai)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.nettigo_air_monitor_bme280_temperature")
    assert state
    assert state.state != STATE_UNAVAILABLE
    assert state.state == "7.56"


async def test_manual_update_entity(menuai: menuai) -> None:
    """Test manual update entity via service homeasasistant/update_entity."""
    nam_data = await async_load_json_object_fixture(menuai, "nam_data.json", DOMAIN)

    await init_integration(menuai)

    await async_setup_component(menuai, "menuai", {})

    update_response = Mock(json=AsyncMock(return_value=nam_data))
    with (
        patch("menuai.components.nam.NettigoAirMonitor.initialize"),
        patch(
            "menuai.components.nam.NettigoAirMonitor._async_http_request",
            return_value=update_response,
        ) as mock_get_data,
    ):
        await menuai.services.async_call(
            "menuai",
            "update_entity",
            {ATTR_ENTITY_ID: ["sensor.nettigo_air_monitor_bme280_temperature"]},
            blocking=True,
        )

    assert mock_get_data.call_count == 1


async def test_unique_id_migration(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Test states of the unique_id migration."""
    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "aa:bb:cc:dd:ee:ff-temperature",
        suggested_object_id="nettigo_air_monitor_dht22_temperature",
        disabled_by=None,
    )

    entity_registry.async_get_or_create(
        SENSOR_DOMAIN,
        DOMAIN,
        "aa:bb:cc:dd:ee:ff-humidity",
        suggested_object_id="nettigo_air_monitor_dht22_humidity",
        disabled_by=None,
    )

    await init_integration(menuai)

    entry = entity_registry.async_get("sensor.nettigo_air_monitor_dht22_temperature")
    assert entry
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff-dht22_temperature"

    entry = entity_registry.async_get("sensor.nettigo_air_monitor_dht22_humidity")
    assert entry
    assert entry.unique_id == "aa:bb:cc:dd:ee:ff-dht22_humidity"
