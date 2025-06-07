"""Test Waze Travel Time sensors."""

import pytest
from pywaze.route_calculator import WRCError

from menuai.components.waze_travel_time.config_flow import WazeConfigFlow
from menuai.components.waze_travel_time.const import (
    CONF_AVOID_FERRIES,
    CONF_AVOID_SUBSCRIPTION_ROADS,
    CONF_AVOID_TOLL_ROADS,
    CONF_EXCL_FILTER,
    CONF_INCL_FILTER,
    CONF_REALTIME,
    CONF_UNITS,
    CONF_VEHICLE_TYPE,
    DEFAULT_OPTIONS,
    DOMAIN,
    IMPERIAL_UNITS,
    METRIC_UNITS,
)
from menuai.core import menuai

from .const import MOCK_CONFIG

from tests.common import MockConfigEntry


@pytest.fixture(name="mock_update_wrcerror")
def mock_update_wrcerror_fixture(mock_update):
    """Mock an update to the sensor failed with WRCError."""
    mock_update.side_effect = WRCError("test")
    return mock_update


@pytest.mark.parametrize(
    ("data", "options"),
    [(MOCK_CONFIG, DEFAULT_OPTIONS)],
)
@pytest.mark.usefixtures("mock_update", "mock_config")
async def test_sensor(menuai: menuai) -> None:
    """Test that sensor works."""
    assert menuai.states.get("sensor.waze_travel_time").state == "150"
    assert (
        menuai.states.get("sensor.waze_travel_time").attributes["attribution"]
        == "Powered by Waze"
    )
    assert menuai.states.get("sensor.waze_travel_time").attributes["duration"] == 150
    assert menuai.states.get("sensor.waze_travel_time").attributes["distance"] == 300
    assert (
        menuai.states.get("sensor.waze_travel_time").attributes["route"]
        == "E1337 - Teststreet"
    )
    assert (
        menuai.states.get("sensor.waze_travel_time").attributes["origin"] == "location1"
    )
    assert (
        menuai.states.get("sensor.waze_travel_time").attributes["destination"]
        == "location2"
    )
    assert (
        menuai.states.get("sensor.waze_travel_time").attributes["unit_of_measurement"]
        == "min"
    )


@pytest.mark.parametrize(
    ("data", "options"),
    [
        (
            MOCK_CONFIG,
            {
                CONF_UNITS: IMPERIAL_UNITS,
                CONF_REALTIME: True,
                CONF_VEHICLE_TYPE: "car",
                CONF_AVOID_TOLL_ROADS: True,
                CONF_AVOID_SUBSCRIPTION_ROADS: True,
                CONF_AVOID_FERRIES: True,
                CONF_INCL_FILTER: [""],
                CONF_EXCL_FILTER: [""],
            },
        )
    ],
)
@pytest.mark.usefixtures("mock_update", "mock_config")
async def test_imperial(menuai: menuai) -> None:
    """Test that the imperial option works."""
    assert menuai.states.get("sensor.waze_travel_time").attributes[
        "distance"
    ] == pytest.approx(186.4113)


@pytest.mark.parametrize(
    ("data", "options"),
    [
        (
            MOCK_CONFIG,
            {
                CONF_UNITS: METRIC_UNITS,
                CONF_REALTIME: True,
                CONF_VEHICLE_TYPE: "car",
                CONF_AVOID_TOLL_ROADS: True,
                CONF_AVOID_SUBSCRIPTION_ROADS: True,
                CONF_AVOID_FERRIES: True,
                CONF_INCL_FILTER: ["IncludeThis"],
                CONF_EXCL_FILTER: [""],
            },
        )
    ],
)
@pytest.mark.usefixtures("mock_update", "mock_config")
async def test_incl_filter(menuai: menuai) -> None:
    """Test that incl_filter only includes route with the wanted street name."""
    assert menuai.states.get("sensor.waze_travel_time").attributes["distance"] == 300


@pytest.mark.parametrize(
    ("data", "options"),
    [
        (
            MOCK_CONFIG,
            {
                CONF_UNITS: METRIC_UNITS,
                CONF_REALTIME: True,
                CONF_VEHICLE_TYPE: "car",
                CONF_AVOID_TOLL_ROADS: True,
                CONF_AVOID_SUBSCRIPTION_ROADS: True,
                CONF_AVOID_FERRIES: True,
                CONF_INCL_FILTER: [""],
                CONF_EXCL_FILTER: ["ExcludeThis"],
            },
        )
    ],
)
@pytest.mark.usefixtures("mock_update", "mock_config")
async def test_excl_filter(menuai: menuai) -> None:
    """Test that excl_filter only includes route without the street name."""
    assert menuai.states.get("sensor.waze_travel_time").attributes["distance"] == 300


@pytest.mark.usefixtures("mock_update_wrcerror")
async def test_sensor_failed_wrcerror(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that sensor update fails with log message."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        options=DEFAULT_OPTIONS,
        entry_id="test",
        version=WazeConfigFlow.VERSION,
    )
    config_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()

    assert menuai.states.get("sensor.waze_travel_time").state == "unknown"
    assert "Error on retrieving data: " in caplog.text
