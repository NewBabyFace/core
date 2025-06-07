"""Test the INKBIRD config flow."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from inkbird_ble import (
    DeviceKey,
    INKBIRDBluetoothDeviceData,
    SensorDescription,
    SensorDeviceInfo,
    SensorUpdate,
    SensorValue,
    Units,
)
from inkbird_ble.parser import Model
from sensor_state_data import SensorDeviceClass

from menuai.components.inkbird.const import (
    CONF_DEVICE_DATA,
    CONF_DEVICE_TYPE,
    DOMAIN,
)
from menuai.components.inkbird.coordinator import FALLBACK_POLL_INTERVAL
from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.config_entries import ConfigEntryState
from menuai.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import (
    IAM_T1_SERVICE_INFO,
    IBS_P02B_SERVICE_INFO,
    SPS_PASSIVE_SERVICE_INFO,
    SPS_SERVICE_INFO,
    SPS_WITH_CORRUPT_NAME_SERVICE_INFO,
)

from tests.common import MockConfigEntry, async_fire_time_changed
from tests.components.bluetooth import inject_bluetooth_service_info


def _make_sensor_update(name: str, humidity: float) -> SensorUpdate:
    return SensorUpdate(
        title=None,
        devices={
            None: SensorDeviceInfo(
                name=f"{name} EEFF",
                model=name,
                manufacturer="INKBIRD",
                sw_version=None,
                hw_version=None,
            )
        },
        entity_descriptions={
            DeviceKey(key="humidity", device_id=None): SensorDescription(
                device_key=DeviceKey(key="humidity", device_id=None),
                device_class=SensorDeviceClass.HUMIDITY,
                native_unit_of_measurement=Units.PERCENTAGE,
            ),
        },
        entity_values={
            DeviceKey(key="humidity", device_id=None): SensorValue(
                device_key=DeviceKey(key="humidity", device_id=None),
                name="Humidity",
                native_value=humidity,
            ),
        },
    )


async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="61DE521B-F0BF-9F44-64D4-75BBE1738105",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, SPS_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    temp_sensor = menuai.states.get("sensor.ibs_th_8105_battery")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "87"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "IBS-TH 8105 Battery"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    # Make sure we remember the device type
    # in case the name is corrupted later
    assert entry.data[CONF_DEVICE_TYPE] == "IBS-TH"
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_device_with_corrupt_name(menuai: menuai) -> None:
    """Test setting up a known device type with a corrupt name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={CONF_DEVICE_TYPE: "IBS-TH"},
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, SPS_WITH_CORRUPT_NAME_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 3

    temp_sensor = menuai.states.get("sensor.ibs_th_eeff_battery")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "87"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "IBS-TH EEFF Battery"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    assert entry.data[CONF_DEVICE_TYPE] == "IBS-TH"
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_polling_sensor(menuai: menuai) -> None:
    """Test setting up a device that needs polling."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={CONF_DEVICE_TYPE: "IBS-TH"},
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0

    with patch(
        "menuai.components.inkbird.coordinator.INKBIRDBluetoothDeviceData.async_poll",
        return_value=_make_sensor_update("IBS-TH", 10.24),
    ):
        inject_bluetooth_service_info(menuai, SPS_PASSIVE_SERVICE_INFO)
        await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 1

    temp_sensor = menuai.states.get("sensor.ibs_th_eeff_humidity")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "10.24"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "IBS-TH EEFF Humidity"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    assert entry.data[CONF_DEVICE_TYPE] == "IBS-TH"

    with patch(
        "menuai.components.inkbird.coordinator.INKBIRDBluetoothDeviceData.async_poll",
        return_value=_make_sensor_update("IBS-TH", 20.24),
    ):
        async_fire_time_changed(menuai, dt_util.utcnow() + FALLBACK_POLL_INTERVAL)
        inject_bluetooth_service_info(menuai, SPS_PASSIVE_SERVICE_INFO)
        await menuai.async_block_till_done()

    temp_sensor = menuai.states.get("sensor.ibs_th_eeff_humidity")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "20.24"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


async def test_notify_sensor_no_advertisement(menuai: menuai) -> None:
    """Test setting up a notify sensor that has no advertisement."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="62:00:A1:3C:AE:7B",
        data={CONF_DEVICE_TYPE: "IAM-T1"},
    )
    entry.add_to_menuai(menuai)

    assert not await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_notify_sensor(menuai: menuai) -> None:
    """Test setting up a notify sensor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="62:00:A1:3C:AE:7B",
        data={CONF_DEVICE_TYPE: "IAM-T1"},
    )
    entry.add_to_menuai(menuai)
    inject_bluetooth_service_info(menuai, IAM_T1_SERVICE_INFO)
    saved_update_callback = None
    saved_device_data_changed_callback = None

    class MockINKBIRDBluetoothDeviceData(INKBIRDBluetoothDeviceData):
        def __init__(
            self,
            device_type: Model | str | None = None,
            device_data: dict[str, Any] | None = None,
            update_callback: Callable[[SensorUpdate], None] | None = None,
            device_data_changed_callback: Callable[[dict[str, Any]], None]
            | None = None,
        ) -> None:
            nonlocal saved_update_callback
            nonlocal saved_device_data_changed_callback
            saved_update_callback = update_callback
            saved_device_data_changed_callback = device_data_changed_callback
            super().__init__(
                device_type=device_type,
                device_data=device_data,
                update_callback=update_callback,
                device_data_changed_callback=device_data_changed_callback,
            )

    mock_client = MagicMock(start_notify=AsyncMock(), disconnect=AsyncMock())
    with (
        patch(
            "menuai.components.inkbird.coordinator.INKBIRDBluetoothDeviceData",
            MockINKBIRDBluetoothDeviceData,
        ),
        patch("inkbird_ble.parser.establish_connection", return_value=mock_client),
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert len(menuai.states.async_all()) == 0

    saved_update_callback(_make_sensor_update("IAM-T1", 10.24))

    assert len(menuai.states.async_all()) == 1

    temp_sensor = menuai.states.get("sensor.iam_t1_eeff_humidity")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "10.24"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "IAM-T1 EEFF Humidity"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    assert entry.data[CONF_DEVICE_TYPE] == "IAM-T1"

    saved_device_data_changed_callback({"temp_unit": "F"})
    assert entry.data[CONF_DEVICE_DATA] == {"temp_unit": "F"}

    saved_device_data_changed_callback({"temp_unit": "C"})
    assert entry.data[CONF_DEVICE_DATA] == {"temp_unit": "C"}

    saved_device_data_changed_callback({"temp_unit": "C"})
    assert entry.data[CONF_DEVICE_DATA] == {"temp_unit": "C"}


async def test_ibs_p02b_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors for an IBS-P02B."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="49:24:11:18:00:65",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, IBS_P02B_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 2

    temp_sensor = menuai.states.get("sensor.ibs_p02b_0065_battery")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "95"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "IBS-P02B 0065 Battery"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    temp_sensor = menuai.states.get("sensor.ibs_p02b_0065_temperature")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "36.6"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "IBS-P02B 0065 Temperature"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    # Make sure we remember the device type
    # in case the name is corrupted later
    assert entry.data[CONF_DEVICE_TYPE] == "IBS-P02B"
    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
