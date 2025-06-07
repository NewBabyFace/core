"""The test for the Trafikverket sensor platform."""

from __future__ import annotations

import pytest
from pytrafikverket import CameraInfoModel

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    load_int: ConfigEntry,
    get_camera: CameraInfoModel,
) -> None:
    """Test the Trafikverket Camera sensor."""

    state = menuai.states.get("sensor.test_camera_direction")
    assert state.state == "180"
    state = menuai.states.get("sensor.test_camera_modified")
    assert state.state == "2022-04-04T04:04:04+00:00"
    state = menuai.states.get("sensor.test_camera_photo_time")
    assert state.state == "2022-04-04T04:04:04+00:00"
    state = menuai.states.get("sensor.test_camera_photo_url")
    assert state.state == "https://www.testurl.com/test_photo.jpg"
    state = menuai.states.get("sensor.test_camera_status")
    assert state.state == "Running"
    state = menuai.states.get("sensor.test_camera_camera_type")
    assert state.state == "Road"
