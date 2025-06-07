"""The tests for Lidarr sensor platform."""

import pytest

from menuai.components.sensor import CONF_STATE_CLASS, SensorStateClass
from menuai.const import ATTR_UNIT_OF_MEASUREMENT
from menuai.core import menuai

from .conftest import ComponentSetup


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    setup_integration: ComponentSetup,
    connection,
) -> None:
    """Test for successfully setting up the Lidarr platform."""
    await setup_integration()

    state = menuai.states.get("sensor.mock_title_disk_space")
    assert state.state == "0.93"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "GB"
    state = menuai.states.get("sensor.mock_title_queue")
    assert state.state == "2"
    assert state.attributes.get("string") == "stopped"
    assert state.attributes.get("string2") == "downloading"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "albums"
    assert state.attributes.get(CONF_STATE_CLASS) == SensorStateClass.TOTAL
    state = menuai.states.get("sensor.mock_title_wanted")
    assert state.state == "1"
    assert state.attributes.get("test") == "test"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "albums"
    assert state.attributes.get(CONF_STATE_CLASS) == SensorStateClass.TOTAL
    state = menuai.states.get("sensor.mock_title_albums")
    assert state.state == "1"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "albums"
    assert state.attributes.get(CONF_STATE_CLASS) == SensorStateClass.TOTAL
