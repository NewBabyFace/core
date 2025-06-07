"""Tests for rainforest eagle sensors."""

from menuai.components.rainforest_eagle.const import DOMAIN
from menuai.core import menuai

from . import MOCK_200_RESPONSE_WITH_PRICE


async def test_sensors_200(menuai: menuai, setup_rainforest_200) -> None:
    """Test the sensors."""
    assert len(menuai.states.async_all()) == 3

    demand = menuai.states.get("sensor.eagle_200_power_demand")
    assert demand is not None
    assert demand.state == "1.152000"
    assert demand.attributes["unit_of_measurement"] == "kW"

    delivered = menuai.states.get("sensor.eagle_200_total_energy_delivered")
    assert delivered is not None
    assert delivered.state == "45251.285000"
    assert delivered.attributes["unit_of_measurement"] == "kWh"

    received = menuai.states.get("sensor.eagle_200_total_energy_received")
    assert received is not None
    assert received.state == "232.232000"
    assert received.attributes["unit_of_measurement"] == "kWh"

    setup_rainforest_200.get_device_query.return_value = MOCK_200_RESPONSE_WITH_PRICE

    config_entry = menuai.config_entries.async_entries(DOMAIN)[0]
    await menuai.config_entries.async_reload(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_all()) == 4

    price = menuai.states.get("sensor.eagle_200_energy_price")
    assert price is not None
    assert price.state == "0.053990"
    assert price.attributes["unit_of_measurement"] == "USD/kWh"


async def test_sensors_100(menuai: menuai, setup_rainforest_100) -> None:
    """Test the sensors."""
    assert len(menuai.states.async_all()) == 3

    demand = menuai.states.get("sensor.eagle_100_power_demand")
    assert demand is not None
    assert demand.state == "1.152000"
    assert demand.attributes["unit_of_measurement"] == "kW"

    delivered = menuai.states.get("sensor.eagle_100_total_energy_delivered")
    assert delivered is not None
    assert delivered.state == "45251.285000"
    assert delivered.attributes["unit_of_measurement"] == "kWh"

    received = menuai.states.get("sensor.eagle_100_total_energy_received")
    assert received is not None
    assert received.state == "232.232000"
    assert received.attributes["unit_of_measurement"] == "kWh"
