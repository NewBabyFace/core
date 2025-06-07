"""The sensor tests for the IPMA platform."""

from unittest.mock import patch

from menuai.core import menuai

from . import ENTRY_CONFIG, MockLocation

from tests.common import MockConfigEntry


async def test_ipma_fire_risk_create_sensors(menuai: menuai) -> None:
    """Test creation of fire risk sensors."""

    with patch("pyipma.location.Location.get", return_value=MockLocation()):
        entry = MockConfigEntry(domain="ipma", data=ENTRY_CONFIG)
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.hometown_fire_risk")

    assert state.state == "3"


async def test_ipma_uv_index_create_sensors(menuai: menuai) -> None:
    """Test creation of uv index sensors."""

    with patch("pyipma.location.Location.get", return_value=MockLocation()):
        entry = MockConfigEntry(domain="ipma", data=ENTRY_CONFIG)
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.hometown_uv_index")

    assert state.state == "6"


async def test_ipma_warning_create_sensors(menuai: menuai) -> None:
    """Test creation of warning sensors."""

    with patch("pyipma.location.Location.get", return_value=MockLocation()):
        entry = MockConfigEntry(domain="ipma", data=ENTRY_CONFIG)
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    state = menuai.states.get("sensor.hometown_weather_alert")

    assert state.state == "yellow"

    assert state.attributes["awarenessTypeName"] == "Agitação Marítima"
