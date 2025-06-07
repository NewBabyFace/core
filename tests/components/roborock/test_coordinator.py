"""Test Roborock Coordinator specific logic."""

import copy
from datetime import timedelta
from unittest.mock import patch

import pytest
from roborock.exceptions import RoborockException

from menuai.components.roborock.const import (
    V1_CLOUD_IN_CLEANING_INTERVAL,
    V1_CLOUD_NOT_CLEANING_INTERVAL,
    V1_LOCAL_IN_CLEANING_INTERVAL,
    V1_LOCAL_NOT_CLEANING_INTERVAL,
)
from menuai.const import Platform
from menuai.core import menuai
from menuai.util import dt as dt_util

from .mock_data import PROP

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.fixture
def platforms() -> list[Platform]:
    """Fixture to set platforms used in the test."""
    return [Platform.SENSOR]


@pytest.mark.parametrize(
    ("interval", "in_cleaning"),
    [
        (V1_CLOUD_IN_CLEANING_INTERVAL, 1),
        (V1_CLOUD_NOT_CLEANING_INTERVAL, 0),
    ],
)
async def test_dynamic_cloud_scan_interval(
    menuai: menuai,
    mock_roborock_entry: MockConfigEntry,
    bypass_api_fixture_v1_only,
    interval: timedelta,
    in_cleaning: int,
) -> None:
    """Test dynamic scan interval."""
    prop = copy.deepcopy(PROP)
    prop.status.in_cleaning = in_cleaning
    with (
        # Force the system to use the cloud api.
        patch(
            "menuai.components.roborock.coordinator.RoborockLocalClientV1.ping",
            side_effect=RoborockException(),
        ),
        patch(
            "menuai.components.roborock.RoborockMqttClientV1.get_prop",
            return_value=prop,
        ),
    ):
        await menuai.config_entries.async_setup(mock_roborock_entry.entry_id)
    assert menuai.states.get("sensor.roborock_s7_maxv_battery").state == "100"
    prop = copy.deepcopy(prop)
    prop.status.battery = 20
    with patch(
        "menuai.components.roborock.RoborockMqttClientV1.get_prop",
        return_value=prop,
    ):
        async_fire_time_changed(
            menuai, dt_util.utcnow() + interval - timedelta(seconds=5)
        )
        assert menuai.states.get("sensor.roborock_s7_maxv_battery").state == "100"
        async_fire_time_changed(menuai, dt_util.utcnow() + interval)

    assert menuai.states.get("sensor.roborock_s7_maxv_battery").state == "20"


@pytest.mark.parametrize(
    ("interval", "in_cleaning"),
    [
        (V1_LOCAL_IN_CLEANING_INTERVAL, 1),
        (V1_LOCAL_NOT_CLEANING_INTERVAL, 0),
    ],
)
async def test_dynamic_local_scan_interval(
    menuai: menuai,
    mock_roborock_entry: MockConfigEntry,
    bypass_api_fixture_v1_only,
    interval: timedelta,
    in_cleaning: int,
) -> None:
    """Test dynamic scan interval."""
    prop = copy.deepcopy(PROP)
    prop.status.in_cleaning = in_cleaning
    with (
        patch(
            "menuai.components.roborock.coordinator.RoborockLocalClientV1.get_prop",
            return_value=prop,
        ),
    ):
        await menuai.config_entries.async_setup(mock_roborock_entry.entry_id)
    assert menuai.states.get("sensor.roborock_s7_maxv_battery").state == "100"
    prop = copy.deepcopy(prop)
    prop.status.battery = 20
    with patch(
        "menuai.components.roborock.coordinator.RoborockLocalClientV1.get_prop",
        return_value=prop,
    ):
        async_fire_time_changed(
            menuai, dt_util.utcnow() + interval - timedelta(seconds=5)
        )
        assert menuai.states.get("sensor.roborock_s7_maxv_battery").state == "100"

        async_fire_time_changed(menuai, dt_util.utcnow() + interval)

    assert menuai.states.get("sensor.roborock_s7_maxv_battery").state == "20"
