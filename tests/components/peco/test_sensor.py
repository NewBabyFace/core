"""Test the PECO Outage Counter sensors."""

from unittest.mock import patch

from peco import AlertResults, OutageResults
import pytest

from menuai.components.peco.const import DOMAIN
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from tests.common import MockConfigEntry

MOCK_ENTRY_DATA = {"county": "TOTAL"}
COUNTY_ENTRY_DATA = {"county": "BUCKS"}
INVALID_COUNTY_DATA = {"county": "INVALID"}


@pytest.mark.parametrize(
    ("sensor", "expected"),
    [
        ("customers_out", "123"),
        ("percent_customers_out", "15"),
        ("outage_count", "456"),
        ("customers_served", "789"),
    ],
)
async def test_sensor_available(
    menuai: menuai, sensor: str, expected: str
) -> None:
    """Test that the sensors are working."""
    # Totals Test

    config_entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "peco.PecoOutageApi.get_outage_totals",
            return_value=OutageResults(
                customers_out=123,
                percent_customers_out=15,
                outage_count=456,
                customers_served=789,
            ),
        ),
        patch(
            "peco.PecoOutageApi.get_map_alerts",
            return_value=AlertResults(
                alert_content="Testing 1234", alert_title="Testing 4321"
            ),
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()
    assert menuai.data[DOMAIN]

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert config_entry.state is ConfigEntryState.LOADED

    sensor_entity = menuai.states.get(f"sensor.total_{sensor}")
    assert sensor_entity is not None
    assert sensor_entity.state != "unavailable"
    assert sensor_entity.state == expected

    # County Test

    config_entry = MockConfigEntry(domain=DOMAIN, data=COUNTY_ENTRY_DATA)
    config_entry.add_to_menuai(menuai)

    with (
        patch(
            "peco.PecoOutageApi.get_outage_count",
            return_value=OutageResults(
                customers_out=123,
                percent_customers_out=15,
                outage_count=456,
                customers_served=789,
            ),
        ),
        patch(
            "peco.PecoOutageApi.get_map_alerts",
            return_value=AlertResults(
                alert_content="Testing 1234", alert_title="Testing 4321"
            ),
        ),
    ):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)
        await menuai.async_block_till_done()

    entries = menuai.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    assert config_entry.state is ConfigEntryState.LOADED

    sensor_entity = menuai.states.get(f"sensor.bucks_{sensor}")
    assert sensor_entity is not None
    assert sensor_entity.state != "unavailable"
    assert sensor_entity.state == expected
