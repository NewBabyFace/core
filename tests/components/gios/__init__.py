"""Tests for GIOS."""

import json
from unittest.mock import patch

from menuai.components.gios.const import DOMAIN
from menuai.core import menuai

from tests.common import MockConfigEntry, async_load_fixture

STATIONS = [
    {"id": 123, "stationName": "Test Name 1", "gegrLat": "99.99", "gegrLon": "88.88"},
    {"id": 321, "stationName": "Test Name 2", "gegrLat": "77.77", "gegrLon": "66.66"},
]


async def init_integration(
    menuai: menuai, incomplete_data=False, invalid_indexes=False
) -> MockConfigEntry:
    """Set up the GIOS integration in MenuAI."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="123",
        data={"station_id": 123, "name": "Home"},
        entry_id="86129426118ae32020417a53712d6eef",
    )

    indexes = json.loads(await async_load_fixture(menuai, "indexes.json", DOMAIN))
    station = json.loads(await async_load_fixture(menuai, "station.json", DOMAIN))
    sensors = json.loads(await async_load_fixture(menuai, "sensors.json", DOMAIN))
    if incomplete_data:
        indexes["stIndexLevel"]["indexLevelName"] = "foo"
        sensors["pm10"]["values"][0]["value"] = None
        sensors["pm10"]["values"][1]["value"] = None
    if invalid_indexes:
        indexes = {}

    with (
        patch(
            "menuai.components.gios.coordinator.Gios._get_stations",
            return_value=STATIONS,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_station",
            return_value=station,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_all_sensors",
            return_value=sensors,
        ),
        patch(
            "menuai.components.gios.coordinator.Gios._get_indexes",
            return_value=indexes,
        ),
    ):
        entry.add_to_menuai(menuai)
        await menuai.config_entries.async_setup(entry.entry_id)
        await menuai.async_block_till_done()

    return entry
