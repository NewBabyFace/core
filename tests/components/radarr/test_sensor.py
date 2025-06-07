"""The tests for Radarr sensor platform."""

from datetime import timedelta
from unittest.mock import patch

from aiopyarr.exceptions import ArrConnectionException
import pytest

from menuai.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from menuai.config_entries import ConfigEntryState
from menuai.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
)
from menuai.core import menuai
from menuai.util import dt as dt_util

from . import setup_integration

from tests.common import async_fire_time_changed
from tests.test_util.aiohttp import AiohttpClientMocker


@pytest.mark.freeze_time("2021-12-03 00:00:00+00:00")
@pytest.mark.parametrize(
    ("windows", "single", "root_folder"),
    [
        (
            False,
            False,
            "downloads",
        ),
        (
            False,
            True,
            "downloads",
        ),
        (
            True,
            False,
            "tv",
        ),
        (
            True,
            True,
            "tv",
        ),
    ],
)
@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    aioclient_mock: AiohttpClientMocker,
    windows: bool,
    single: bool,
    root_folder: str,
) -> None:
    """Test for successfully setting up the Radarr platform."""
    await setup_integration(menuai, aioclient_mock, windows=windows, single_return=single)

    state = menuai.states.get(f"sensor.mock_title_disk_space_{root_folder}")
    assert state.state == "263.10"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "GB"
    state = menuai.states.get("sensor.mock_title_movies")
    assert state.state == "1"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "movies"
    state = menuai.states.get("sensor.mock_title_start_time")
    assert state.state == "2020-09-01T23:50:20+00:00"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.TIMESTAMP
    state = menuai.states.get("sensor.mock_title_queue")
    assert state.state == "2"
    assert state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) == "movies"
    assert state.attributes.get(ATTR_STATE_CLASS) is SensorStateClass.TOTAL


@pytest.mark.freeze_time("2021-12-03 00:00:00+00:00")
async def test_windows(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test for successfully setting up the Radarr platform on Windows."""
    await setup_integration(menuai, aioclient_mock, windows=True)

    state = menuai.states.get("sensor.mock_title_disk_space_tv")
    assert state.state == "263.10"


async def test_update_failed(
    menuai: menuai, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test coordinator updates handle failures."""
    entry = await setup_integration(menuai, aioclient_mock)
    assert entry.state is ConfigEntryState.LOADED
    entity = "sensor.mock_title_disk_space_downloads"
    assert menuai.states.get(entity).state == "263.10"

    with patch(
        "menuai.components.radarr.RadarrClient._async_request",
        side_effect=ArrConnectionException,
    ) as updater:
        next_update = dt_util.utcnow() + timedelta(minutes=1)
        async_fire_time_changed(menuai, next_update)
        await menuai.async_block_till_done()
        assert updater.call_count == 2
        assert menuai.states.get(entity).state == STATE_UNAVAILABLE

    next_update = dt_util.utcnow() + timedelta(minutes=1)
    async_fire_time_changed(menuai, next_update)
    await menuai.async_block_till_done()
    assert menuai.states.get(entity).state == "263.10"
