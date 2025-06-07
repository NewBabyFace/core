"""Test the switchbot sensors."""

from unittest.mock import AsyncMock, patch

import pytest

from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.components.switchbot.const import (
    CONF_ENCRYPTION_KEY,
    CONF_KEY_ID,
    DOMAIN,
)
from menuai.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SENSOR_TYPE,
)
from menuai.core import menuai
from menuai.setup import async_setup_component

from . import (
    CIRCULATOR_FAN_SERVICE_INFO,
    HUB3_SERVICE_INFO,
    HUBMINI_MATTER_SERVICE_INFO,
    LEAK_SERVICE_INFO,
    REMOTE_SERVICE_INFO,
    WOHAND_SERVICE_INFO,
    WOHUB2_SERVICE_INFO,
    WOMETERTHPC_SERVICE_INFO,
    WORELAY_SWITCH_1PM_SERVICE_INFO,
)

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, WOHAND_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "bot",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 2

    battery_sensor = menuai.states.get("sensor.test_name_battery")
    battery_sensor_attrs = battery_sensor.attributes
    assert battery_sensor.state == "89"
    assert battery_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Battery"
    assert battery_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert battery_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_co2_sensor(menuai: menuai) -> None:
    """Test setting up creates the co2 sensor for a WoTHPc."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, WOMETERTHPC_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:AA",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "hygrometer_co2",
        },
        unique_id="aabbccddeeaa",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 5

    battery_sensor = menuai.states.get("sensor.test_name_battery")
    battery_sensor_attrs = battery_sensor.attributes
    assert battery_sensor.state == "100"
    assert battery_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Battery"
    assert battery_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert battery_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    co2_sensor = menuai.states.get("sensor.test_name_carbon_dioxide")
    co2_sensor_attrs = co2_sensor.attributes
    assert co2_sensor.state == "725"
    assert co2_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Carbon dioxide"
    assert co2_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "ppm"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_relay_switch_1pm_sensor(menuai: menuai) -> None:
    """Test setting up creates the relay switch 1PM sensor."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, WORELAY_SWITCH_1PM_SERVICE_INFO)

    with patch(
        "menuai.components.switchbot.switch.switchbot.SwitchbotRelaySwitch.get_basic_info",
        new=AsyncMock(
            return_value={
                "power": 4.9,
                "current": 0.02,
                "voltage": 25,
                "energy": 0.2,
            }
        ),
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
                CONF_NAME: "test-name",
                CONF_SENSOR_TYPE: "relay_switch_1pm",
                CONF_KEY_ID: "ff",
                CONF_ENCRYPTION_KEY: "ffffffffffffffffffffffffffffffff",
            },
            unique_id="aabbccddeeaa",
        )
        entry.add_to_menuai(menuai)

        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 5

    power_sensor = menuai.states.get("sensor.test_name_power")
    power_sensor_attrs = power_sensor.attributes
    assert power_sensor.state == "4.9"
    assert power_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Power"
    assert power_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "W"
    assert power_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    voltage_sensor = menuai.states.get("sensor.test_name_voltage")
    voltage_sensor_attrs = voltage_sensor.attributes
    assert voltage_sensor.state == "25"
    assert voltage_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Voltage"
    assert voltage_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "V"
    assert voltage_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    current_sensor = menuai.states.get("sensor.test_name_current")
    current_sensor_attrs = current_sensor.attributes
    assert current_sensor.state == "0.02"
    assert current_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Current"
    assert current_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "A"
    assert current_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    energy_sensor = menuai.states.get("sensor.test_name_energy")
    energy_sensor_attrs = energy_sensor.attributes
    assert energy_sensor.state == "0.2"
    assert energy_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Energy"
    assert energy_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "kWh"
    assert energy_sensor_attrs[ATTR_STATE_CLASS] == "total_increasing"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"
    assert rssi_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_leak_sensor(menuai: menuai) -> None:
    """Test setting up the leak detector."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, LEAK_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: "test-name",
            CONF_SENSOR_TYPE: "leak",
        },
        unique_id="aabbccddeeaa",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    battery_sensor = menuai.states.get("sensor.test_name_battery")
    battery_sensor_attrs = battery_sensor.attributes
    assert battery_sensor.state == "86"
    assert battery_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Battery"
    assert battery_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert battery_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    leak_sensor = menuai.states.get("binary_sensor.test_name")
    leak_sensor_attrs = leak_sensor.attributes
    assert leak_sensor.state == "off"
    assert leak_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_remote(menuai: menuai) -> None:
    """Test setting up the remote sensor."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, REMOTE_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: "test-name",
            CONF_SENSOR_TYPE: "remote",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 2

    battery_sensor = menuai.states.get("sensor.test_name_battery")
    battery_sensor_attrs = battery_sensor.attributes
    assert battery_sensor.state == "86"
    assert battery_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Battery"
    assert battery_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert battery_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_hub2_sensor(menuai: menuai) -> None:
    """Test setting up creates the sensor for WoHub2."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, WOHUB2_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_SENSOR_TYPE: "hub2",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 5

    temperature_sensor = menuai.states.get("sensor.test_name_temperature")
    temperature_sensor_attrs = temperature_sensor.attributes
    assert temperature_sensor.state == "26.4"
    assert temperature_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Temperature"
    assert temperature_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert temperature_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    humidity_sensor = menuai.states.get("sensor.test_name_humidity")
    humidity_sensor_attrs = humidity_sensor.attributes
    assert humidity_sensor.state == "44"
    assert humidity_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Humidity"
    assert humidity_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert humidity_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    light_level_sensor = menuai.states.get("sensor.test_name_light_level")
    light_level_sensor_attrs = light_level_sensor.attributes
    assert light_level_sensor.state == "4"
    assert light_level_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Light level"
    assert light_level_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "Level"

    light_level_sensor = menuai.states.get("sensor.test_name_illuminance")
    light_level_sensor_attrs = light_level_sensor.attributes
    assert light_level_sensor.state == "30"
    assert light_level_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Illuminance"
    assert light_level_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "lx"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_hubmini_matter_sensor(menuai: menuai) -> None:
    """Test setting up creates the sensor for HubMini Matter."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, HUBMINI_MATTER_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_SENSOR_TYPE: "hubmini_matter",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 3

    temperature_sensor = menuai.states.get("sensor.test_name_temperature")
    temperature_sensor_attrs = temperature_sensor.attributes
    assert temperature_sensor.state == "24.1"
    assert temperature_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Temperature"
    assert temperature_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert temperature_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    humidity_sensor = menuai.states.get("sensor.test_name_humidity")
    humidity_sensor_attrs = humidity_sensor.attributes
    assert humidity_sensor.state == "53"
    assert humidity_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Humidity"
    assert humidity_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert humidity_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_fan_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, CIRCULATOR_FAN_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "aa:bb:cc:dd:ee:ff",
            CONF_NAME: "test-name",
            CONF_PASSWORD: "test-password",
            CONF_SENSOR_TYPE: "circulator_fan",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_menuai(menuai)

    with patch(
        "menuai.components.switchbot.fan.switchbot.SwitchbotFan.update",
        return_value=True,
    ):
        assert await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

        assert len(menuai.states.async_all("sensor")) == 2

        battery_sensor = menuai.states.get("sensor.test_name_battery")
        battery_sensor_attrs = battery_sensor.attributes
        assert battery_sensor.state == "82"
        assert battery_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Battery"
        assert battery_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
        assert battery_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

        rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
        rssi_sensor_attrs = rssi_sensor.attributes
        assert rssi_sensor.state == "-60"
        assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
        assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

        assert await menuai.config_entries.async_unload(entry.entry_id)
        await menuai.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_hub3_sensor(menuai: menuai) -> None:
    """Test setting up creates the sensor for Hub3."""
    await async_setup_component(menuai, DOMAIN, {})
    inject_bluetooth_service_info(menuai, HUB3_SERVICE_INFO)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_ADDRESS: "AA:BB:CC:DD:EE:FF",
            CONF_NAME: "test-name",
            CONF_SENSOR_TYPE: "hub3",
        },
        unique_id="aabbccddeeff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 5

    temperature_sensor = menuai.states.get("sensor.test_name_temperature")
    temperature_sensor_attrs = temperature_sensor.attributes
    assert temperature_sensor.state == "25.3"
    assert temperature_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Temperature"
    assert temperature_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "°C"
    assert temperature_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    humidity_sensor = menuai.states.get("sensor.test_name_humidity")
    humidity_sensor_attrs = humidity_sensor.attributes
    assert humidity_sensor.state == "52"
    assert humidity_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Humidity"
    assert humidity_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert humidity_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    rssi_sensor = menuai.states.get("sensor.test_name_bluetooth_signal")
    rssi_sensor_attrs = rssi_sensor.attributes
    assert rssi_sensor.state == "-60"
    assert rssi_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Bluetooth signal"
    assert rssi_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "dBm"

    light_level_sensor = menuai.states.get("sensor.test_name_light_level")
    light_level_sensor_attrs = light_level_sensor.attributes
    assert light_level_sensor.state == "3"
    assert light_level_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Light level"
    assert light_level_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "Level"
    assert light_level_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    illuminance_sensor = menuai.states.get("sensor.test_name_illuminance")
    illuminance_sensor_attrs = illuminance_sensor.attributes
    assert illuminance_sensor.state == "90"
    assert illuminance_sensor_attrs[ATTR_FRIENDLY_NAME] == "test-name Illuminance"
    assert illuminance_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "lx"
    assert illuminance_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
