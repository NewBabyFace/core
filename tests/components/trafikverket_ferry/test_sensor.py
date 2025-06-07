"""The test for the Trafikverket sensor platform."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from pytrafikverket.models import FerryStopModel

from menuai.config_entries import ConfigEntry
from menuai.core import menuai
from menuai.util import dt as dt_util

from tests.common import async_fire_time_changed


async def test_sensor(
    menuai: menuai,
    load_int: ConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
    get_ferries: list[FerryStopModel],
) -> None:
    """Test the Trafikverket Ferry sensor."""
    state1 = menuai.states.get("sensor.harbor1_departure_from")
    state2 = menuai.states.get("sensor.harbor1_departure_to")
    state3 = menuai.states.get("sensor.harbor1_departure_time")
    assert state1.state == "Harbor 1"
    assert state2.state == "Harbor 2"
    assert state3.state == str(dt_util.now().year + 1) + "-05-01T12:00:00+00:00"
    assert state1.attributes["other_information"] == [""]

    monkeypatch.setattr(get_ferries[0], "other_information", ["Nothing exiting"])

    with patch(
        "menuai.components.trafikverket_ferry.coordinator.TrafikverketFerry.async_get_next_ferry_stops",
        return_value=get_ferries,
    ):
        async_fire_time_changed(
            menuai,
            dt_util.utcnow() + timedelta(minutes=6),
        )
        await menuai.async_block_till_done()

    state1 = menuai.states.get("sensor.harbor1_departure_from")
    assert state1.state == "Harbor 1"
    assert state1.attributes["other_information"] == ["Nothing exiting"]
