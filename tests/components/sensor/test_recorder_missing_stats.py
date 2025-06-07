"""The tests for sensor recorder platform can catch up."""

from datetime import datetime, timedelta
import threading
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.recorder import get_instance
from menuai.components.recorder.history import get_significant_states
from menuai.components.recorder.statistics import (
    get_latest_short_term_statistics_with_session,
    statistics_during_period,
)
from menuai.components.recorder.util import session_scope
from menuai.core import CoreState
from menuai.helpers import recorder as recorder_helper
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import async_test_home_assistant
from tests.components.recorder.common import (
    async_wait_recording_done,
    do_adhoc_statistics,
)
from tests.typing import RecorderInstanceContextManager

POWER_SENSOR_ATTRIBUTES = {
    "device_class": "energy",
    "state_class": "measurement",
    "unit_of_measurement": "kWh",
}


@pytest.fixture(autouse=True)
def disable_db_issue_creation():
    """Disable the creation of the database issue."""
    with patch(
        "menuai.components.recorder.util._async_create_mariadb_range_index_regression_issue"
    ):
        yield


@pytest.mark.timeout(25)
@pytest.mark.parametrize("persistent_database", [True])
@pytest.mark.parametrize("enable_missing_statistics", [True])
@pytest.mark.usefixtures("menuai_storage")  # Prevent test menuai from writing to storage
async def test_compile_missing_statistics(
    async_test_recorder: RecorderInstanceContextManager, freezer: FrozenDateTimeFactory
) -> None:
    """Test compile missing statistics."""
    three_days_ago = datetime(2021, 1, 1, 0, 0, 0, tzinfo=dt_util.UTC)
    start_time = three_days_ago + timedelta(days=3)
    freezer.move_to(three_days_ago)
    async with (
        async_test_home_assistant(initial_state=CoreState.not_running) as menuai,
        async_test_recorder(menuai, wait_recorder=False),
    ):
        recorder_helper.async_initialize_recorder(menuai)
        await async_setup_component(menuai, "sensor", {})
        get_instance(menuai).recorder_and_worker_thread_ids.add(threading.get_ident())
        await menuai.async_start()
        await async_wait_recording_done(menuai)
        await async_wait_recording_done(menuai)

        menuai.states.async_set("sensor.test1", "0", POWER_SENSOR_ATTRIBUTES)
        await async_wait_recording_done(menuai)

        two_days_ago = three_days_ago + timedelta(days=1)
        freezer.move_to(two_days_ago)
        do_adhoc_statistics(menuai, start=two_days_ago)
        await async_wait_recording_done(menuai)
        with session_scope(menuai=menuai, read_only=True) as session:
            latest = get_latest_short_term_statistics_with_session(
                menuai, session, {"sensor.test1"}, {"state", "sum"}
            )
        latest_stat = latest["sensor.test1"][0]
        assert latest_stat["start"] == 1609545600.0
        assert latest_stat["end"] == 1609545600.0 + 300
        count = 1
        past_time = two_days_ago
        while past_time <= start_time:
            freezer.move_to(past_time)
            menuai.states.async_set("sensor.test1", str(count), POWER_SENSOR_ATTRIBUTES)
            past_time += timedelta(minutes=5)
            count += 1

        await async_wait_recording_done(menuai)

        states = get_significant_states(
            menuai, three_days_ago, past_time, ["sensor.test1"]
        )
        assert len(states["sensor.test1"]) == 577

        await menuai.async_stop()
        await menuai.async_block_till_done()

    freezer.move_to(start_time)
    async with (
        async_test_home_assistant(initial_state=CoreState.not_running) as menuai,
        async_test_recorder(menuai, wait_recorder=False),
    ):
        recorder_helper.async_initialize_recorder(menuai)
        await async_setup_component(menuai, "sensor", {})
        menuai.states.async_set("sensor.test1", "0", POWER_SENSOR_ATTRIBUTES)
        get_instance(menuai).recorder_and_worker_thread_ids.add(threading.get_ident())
        await menuai.async_start()
        await async_wait_recording_done(menuai)
        await async_wait_recording_done(menuai)
        with session_scope(menuai=menuai, read_only=True) as session:
            latest = get_latest_short_term_statistics_with_session(
                menuai, session, {"sensor.test1"}, {"state", "sum", "max", "mean", "min"}
            )
        latest_stat = latest["sensor.test1"][0]
        assert latest_stat["start"] == 1609718100.0
        assert latest_stat["end"] == 1609718100.0 + 300
        assert latest_stat["mean"] == 576.0
        assert latest_stat["min"] == 575.0
        assert latest_stat["max"] == 576.0
        stats = statistics_during_period(
            menuai,
            two_days_ago,
            start_time,
            units={"energy": "kWh"},
            statistic_ids={"sensor.test1"},
            period="hour",
            types={"mean"},
        )
        # Make sure we have 48 hours of statistics
        assert len(stats["sensor.test1"]) == 48
        # Make sure the last mean is 570.5
        assert stats["sensor.test1"][-1]["mean"] == 570.5
        await menuai.async_stop()
