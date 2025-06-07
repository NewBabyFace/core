"""Test the Leaone sensors."""

from menuai.components.leaone.const import DOMAIN
from menuai.components.sensor import ATTR_STATE_CLASS
from menuai.const import ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT
from menuai.core import menuai

from . import SCALE_SERVICE_INFO, SCALE_SERVICE_INFO_2, SCALE_SERVICE_INFO_3

from tests.common import MockConfigEntry
from tests.components.bluetooth import inject_bluetooth_service_info


async def test_sensors(menuai: menuai) -> None:
    """Test setting up creates the sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="5F:5A:5C:52:D3:94",
    )
    entry.add_to_menuai(menuai)

    assert await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 0

    inject_bluetooth_service_info(menuai, SCALE_SERVICE_INFO)
    await menuai.async_block_till_done()
    inject_bluetooth_service_info(menuai, SCALE_SERVICE_INFO_2)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 2

    mass_sensor = menuai.states.get("sensor.tzc4_d394_mass")
    mass_sensor_attrs = mass_sensor.attributes
    assert mass_sensor.state == "77.11"
    assert mass_sensor_attrs[ATTR_FRIENDLY_NAME] == "TZC4 D394 Mass"
    assert mass_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "kg"
    assert mass_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    mass_sensor = menuai.states.get("sensor.tzc4_d394_non_stabilized_mass")
    mass_sensor_attrs = mass_sensor.attributes
    assert mass_sensor.state == "77.11"
    assert mass_sensor_attrs[ATTR_FRIENDLY_NAME] == "TZC4 D394 Non Stabilized Mass"
    assert mass_sensor_attrs[ATTR_UNIT_OF_MEASUREMENT] == "kg"
    assert mass_sensor_attrs[ATTR_STATE_CLASS] == "measurement"

    inject_bluetooth_service_info(menuai, SCALE_SERVICE_INFO_3)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all("sensor")) == 2

    assert await menuai.config_entries.async_unload(entry.entry_id)
    await menuai.async_block_till_done()
