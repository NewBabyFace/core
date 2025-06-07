"""Tests for the Freebox sensors."""

from copy import deepcopy
from unittest.mock import Mock

from freezegun.api import FrozenDateTimeFactory

from menuai.components.freebox import SCAN_INTERVAL
from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.core import menuai

from .common import setup_platform
from .const import (
    DATA_CONNECTION_GET_STATUS,
    DATA_HOME_GET_NODES,
    DATA_STORAGE_GET_DISKS,
)

from tests.common import async_fire_time_changed


async def test_network_speed(
    menuai: menuai, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test missed call sensor."""
    await setup_platform(menuai, SENSOR_DOMAIN)

    assert menuai.states.get("sensor.freebox_download_speed").state == "198.9"
    assert menuai.states.get("sensor.freebox_upload_speed").state == "1440.0"

    # Simulate a changed speed
    data_connection_get_status_changed = deepcopy(DATA_CONNECTION_GET_STATUS)
    data_connection_get_status_changed["rate_down"] = 123400
    data_connection_get_status_changed["rate_up"] = 432100
    router().connection.get_status.return_value = data_connection_get_status_changed
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    # To execute the save
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.freebox_download_speed").state == "123.4"
    assert menuai.states.get("sensor.freebox_upload_speed").state == "432.1"


async def test_call(
    menuai: menuai, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test missed call sensor."""
    await setup_platform(menuai, SENSOR_DOMAIN)

    assert menuai.states.get("sensor.freebox_missed_calls").state == "3"

    # Simulate we marked calls as read
    data_call_get_calls_marked_as_read = []
    router().call.get_calls_log.return_value = data_call_get_calls_marked_as_read
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    # To execute the save
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.freebox_missed_calls").state == "0"


async def test_disk(
    menuai: menuai, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test disk sensor."""
    await setup_platform(menuai, SENSOR_DOMAIN)

    # Initial state
    assert (
        router().storage.get_disks.return_value[2]["partitions"][0]["total_bytes"]
        == 1960000000000
    )

    assert (
        router().storage.get_disks.return_value[2]["partitions"][0]["free_bytes"]
        == 1730000000000
    )

    assert menuai.states.get("sensor.freebox_free_space").state == "88.27"

    # Simulate a changed storage size
    data_storage_get_disks_changed = deepcopy(DATA_STORAGE_GET_DISKS)
    data_storage_get_disks_changed[2]["partitions"][0]["free_bytes"] = 880000000000
    router().storage.get_disks.return_value = data_storage_get_disks_changed
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    # To execute the save
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.freebox_free_space").state == "44.9"


async def test_battery(
    menuai: menuai, freezer: FrozenDateTimeFactory, router: Mock
) -> None:
    """Test battery sensor."""
    await setup_platform(menuai, SENSOR_DOMAIN)

    assert menuai.states.get("sensor.telecommande_niveau_de_batterie").state == "100"
    assert menuai.states.get("sensor.ouverture_porte_niveau_de_batterie").state == "100"
    assert menuai.states.get("sensor.detecteur_niveau_de_batterie").state == "100"

    # Simulate a changed battery
    data_home_get_nodes_changed = deepcopy(DATA_HOME_GET_NODES)
    data_home_get_nodes_changed[2]["show_endpoints"][3]["value"] = 25
    data_home_get_nodes_changed[3]["show_endpoints"][4]["value"] = 50
    data_home_get_nodes_changed[4]["show_endpoints"][5]["value"] = 75
    router().home.get_home_nodes.return_value = data_home_get_nodes_changed
    # Simulate an update
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    # To execute the save
    await menuai.async_block_till_done()
    assert menuai.states.get("sensor.telecommande_niveau_de_batterie").state == "25"
    assert menuai.states.get("sensor.ouverture_porte_niveau_de_batterie").state == "50"
    assert menuai.states.get("sensor.detecteur_niveau_de_batterie").state == "75"
