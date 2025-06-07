"""Tests for SpeedTest sensors."""

from unittest.mock import MagicMock

from menuai.components.sensor import DOMAIN as SENSOR_DOMAIN
from menuai.components.speedtestdotnet.const import DOMAIN
from menuai.core import menuai

from . import MOCK_RESULTS, MOCK_SERVERS, MOCK_STATES

from tests.common import MockConfigEntry


async def test_speedtestdotnet_sensors(
    menuai: menuai, mock_api: MagicMock
) -> None:
    """Test sensors created for speedtestdotnet integration."""
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_menuai(menuai)

    mock_api.return_value.get_best_server.return_value = MOCK_SERVERS[1][0]
    mock_api.return_value.results.dict.return_value = MOCK_RESULTS

    await menuai.config_entries.async_setup(entry.entry_id)
    await menuai.async_block_till_done()

    assert len(menuai.states.async_entity_ids(SENSOR_DOMAIN)) == 3

    sensor = menuai.states.get("sensor.speedtest_ping")
    assert sensor
    assert sensor.state == MOCK_STATES["ping"]

    sensor = menuai.states.get("sensor.speedtest_download")
    assert sensor
    assert sensor.state == MOCK_STATES["download"]

    sensor = menuai.states.get("sensor.speedtest_ping")
    assert sensor
    assert sensor.state == MOCK_STATES["ping"]
