"""The test for the Trafikverket binary sensor platform."""

from __future__ import annotations

import pytest
from pytrafikverket import CameraInfoModel

from menuai.config_entries import ConfigEntry
from menuai.const import STATE_ON
from menuai.core import menuai


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensor(
    menuai: menuai,
    load_int: ConfigEntry,
    get_camera: CameraInfoModel,
) -> None:
    """Test the Trafikverket Camera binary sensor."""

    state = menuai.states.get("binary_sensor.test_camera_active")
    assert state.state == STATE_ON
