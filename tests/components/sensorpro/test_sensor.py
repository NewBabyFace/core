"""Test the SensorPro sensors."""

from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.components.sensorpro.const import DOMAIN
from menuai.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from menuai.core import menuai

from . import SENSORPRO_SERVICE_INFO

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="aa:bb:cc:dd:ee:ff",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 0
    inject_bluetooth_service_info(menuai, SENSORPRO_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all("sensor")) == 4

    humid_sensor = menuai.states.get("sensor.t201_eeff_humidity")
    humid_sensor_attrs = humid_sensor.attributes
    assert humid_sensor.state == "50.21"
    assert humid_sensor_attrs[ATTR_FRIENDLY_NAME] == "T201 EEFF Humidity"
    assert humid_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "%"
    assert humid_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
