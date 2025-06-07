"""Test the Moat sensors."""

from menuai.components.moat.const import DOMAIN
from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from menuai.core import menuai

from . import MOAT_S2_SERVICE_INFO

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

    assert len(menuai.states.async_all()) == 0
    inject_bluetooth_service_info(menuai, MOAT_S2_SERVICE_INFO)
    await menuai.async_block_till_done()
    assert len(menuai.states.async_all()) == 4

    temp_sensor = menuai.states.get("sensor.moat_s2_eeff_voltage")
    temp_sensor_attribtes = temp_sensor.attributes
    assert temp_sensor.state == "3.061"
    assert temp_sensor_attribtes[ATTR_FRIENDLY_NAME] == "Moat S2 EEFF Voltage"
    assert temp_sensor_attribtes[ATTR_UNIT_OF_MEASUREMENT] == "V"
    assert temp_sensor_attribtes[ATTR_STATE_CLASS] == "measurement"

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
