"""The test for the Trafikverket train utils."""

from __future__ import annotations

from datetime import datetime

from freezegun.api import FrozenDateTimeFactory

from menuai.components.trafikverket_train.util import next_departuredate
from menuai.const import WEEKDAYS
from menuai.util import dt as dt_util


async def test_sensor_next(
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the Trafikverket Train utils."""

    assert next_departuredate(WEEKDAYS) == dt_util.now().date()
    freezer.move_to(datetime(2023, 12, 22))  # Friday
    assert (
        next_departuredate(["mon", "tue", "wed", "thu"])
        == datetime(2023, 12, 25).date()
    )
    freezer.move_to(datetime(2023, 12, 25))  # Monday
    assert next_departuredate(["fri", "sat", "sun"]) == datetime(2023, 12, 29).date()
