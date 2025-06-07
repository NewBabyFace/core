"""Tests for the Freebox binary sensors."""

from copy import deepcopy
from unittest.mock import Mock

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
    BinarySensorDeviceClass,
)
from menuai.components.freebox import SCAN_INTERVAL
from menuai.const import ATTR_DEVICE_CLASS
from menuai.core import menuai

from .common import setup_platform
from .const import DATA_HOME_PIR_GET_VALUE, DATA_STORAGE_GET_RAIDS

from tests.common import async_fire_time_changed


async def test_raid_array_degraded(
    menuai: menuai, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test raid array degraded binary sensor."""
    await setup_platform(menuai, BINARY_SENSOR_DOMAIN)

    assert (
        menuai.states.get("binary_sensor.freebox_server_r2_raid_array_0_degraded").state
        == "off"
    )

    # Now simulate we degraded
    data_storage_get_raids_degraded = deepcopy(DATA_STORAGE_GET_RAIDS)
    data_storage_get_raids_degraded[0]["degraded"] = True
    router().storage.get_raids.return_value = data_storage_get_raids_degraded
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    # To execute the save
    await menuai.async_block_till_done()
    assert (
        menuai.states.get("binary_sensor.freebox_server_r2_raid_array_0_degraded").state
        == "on"
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_home(
    menuai: menuai, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test home binary sensors."""
    await setup_platform(menuai, BINARY_SENSOR_DOMAIN)

    # Device class
    assert (
        menuai.states.get("binary_sensor.detecteur").attributes[ATTR_DEVICE_CLASS]
        == BinarySensorDeviceClass.MOTION
    )
    assert (
        menuai.states.get("binary_sensor.ouverture_porte").attributes[ATTR_DEVICE_CLASS]
        == BinarySensorDeviceClass.DOOR
    )
    assert (
        menuai.states.get("binary_sensor.ouverture_porte_couvercle").attributes[
            ATTR_DEVICE_CLASS
        ]
        == BinarySensorDeviceClass.SAFETY
    )

    # Initial state
    assert menuai.states.get("binary_sensor.detecteur").state == "on"
    assert menuai.states.get("binary_sensor.detecteur_couvercle").state == "off"
    assert menuai.states.get("binary_sensor.ouverture_porte").state == "unknown"
    assert menuai.states.get("binary_sensor.ouverture_porte_couvercle").state == "off"

    # Now simulate a changed status
    data_home_get_values_changed = deepcopy(DATA_HOME_PIR_GET_VALUE)
    data_home_get_values_changed["value"] = True
    router().home.get_home_endpoint_value.return_value = data_home_get_values_changed

    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert menuai.states.get("binary_sensor.detecteur").state == "off"
    assert menuai.states.get("binary_sensor.detecteur_couvercle").state == "on"
    assert menuai.states.get("binary_sensor.ouverture_porte").state == "off"
    assert menuai.states.get("binary_sensor.ouverture_porte_couvercle").state == "on"
