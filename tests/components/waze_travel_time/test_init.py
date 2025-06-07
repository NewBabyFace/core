"""Test waze_travel_time services."""

import pytest

from menuai.components.waze_travel_time.const import (
    CONF_AVOID_FERRIES,
    CONF_AVOID_SUBSCRIPTION_ROADS,
    CONF_AVOID_TOLL_ROADS,
    CONF_EXCL_FILTER,
    CONF_INCL_FILTER,
    CONF_REALTIME,
    CONF_UNITS,
    CONF_VEHICLE_TYPE,
    DEFAULT_AVOID_FERRIES,
    DEFAULT_AVOID_SUBSCRIPTION_ROADS,
    DEFAULT_AVOID_TOLL_ROADS,
    DEFAULT_FILTER,
    DEFAULT_OPTIONS,
    DEFAULT_REALTIME,
    DEFAULT_VEHICLE_TYPE,
    DOMAIN,
    METRIC_UNITS,
)
from menuai.config_entries import ConfigEntryState
from menuai.core import menuai

from .const import MOCK_CONFIG

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    ("data", "options"),
    [(MOCK_CONFIG, DEFAULT_OPTIONS)],
)
@pytest.mark.usefixtures("mock_update", "mock_config")
async def test_service_get_travel_times(menuai: menuai) -> None:
    """Test service get_travel_times."""
    response_data = await menuai.services.async_call(
        "waze_travel_time",
        "get_travel_times",
        {
            "origin": "location1",
            "destination": "location2",
            "vehicle_type": "car",
            "region": "us",
            "units": "imperial",
            "incl_filter": ["IncludeThis"],
        },
        blocking=True,
        return_response=True,
    )
    assert response_data == {
        "routes": [
            {
                "distance": pytest.approx(186.4113),
                "duration": 150,
                "name": "E1337 - Teststreet",
                "street_names": ["E1337", "IncludeThis", "Teststreet"],
            },
        ]
    }


@pytest.mark.usefixtures("mock_update")
async def test_migrate_entry_v1_v2(menuai: menuai) -> None:
    """Test successful migration of entry data."""
    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data=MOCK_CONFIG,
        options={
            CONF_REALTIME: DEFAULT_REALTIME,
            CONF_VEHICLE_TYPE: DEFAULT_VEHICLE_TYPE,
            CONF_UNITS: METRIC_UNITS,
            CONF_AVOID_FERRIES: DEFAULT_AVOID_FERRIES,
            CONF_AVOID_SUBSCRIPTION_ROADS: DEFAULT_AVOID_SUBSCRIPTION_ROADS,
            CONF_AVOID_TOLL_ROADS: DEFAULT_AVOID_TOLL_ROADS,
        },
    )

    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    updated_entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)

    assert updated_entry.state is ConfigEntryState.LOADED
    assert updated_entry.version == 2
    assert updated_entry.options[CONF_INCL_FILTER] == DEFAULT_FILTER
    assert updated_entry.options[CONF_EXCL_FILTER] == DEFAULT_FILTER

    mock_entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data=MOCK_CONFIG,
        options={
            CONF_REALTIME: DEFAULT_REALTIME,
            CONF_VEHICLE_TYPE: DEFAULT_VEHICLE_TYPE,
            CONF_UNITS: METRIC_UNITS,
            CONF_AVOID_FERRIES: DEFAULT_AVOID_FERRIES,
            CONF_AVOID_SUBSCRIPTION_ROADS: DEFAULT_AVOID_SUBSCRIPTION_ROADS,
            CONF_AVOID_TOLL_ROADS: DEFAULT_AVOID_TOLL_ROADS,
            CONF_INCL_FILTER: "include",
            CONF_EXCL_FILTER: "exclude",
        },
    )

    mock_entry.add_to_menuai(menuai)
    await menuai.config_entries.async_setup(mock_entry.entry_id)
    await menuai.async_block_till_done()

    updated_entry = menuai.config_entries.async_get_entry(mock_entry.entry_id)

    assert updated_entry.state is ConfigEntryState.LOADED
    assert updated_entry.version == 2
    assert updated_entry.options[CONF_INCL_FILTER] == ["include"]
    assert updated_entry.options[CONF_EXCL_FILTER] == ["exclude"]
