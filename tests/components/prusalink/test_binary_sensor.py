"""Test Prusalink sensors."""

from unittest.mock import patch

import pytest

from menuai.const import STATE_OFF, Platform
from menuai.core import menuai
from menuai.setup import async_setup_component


@pytest.fixture(autouse=True)
def setup_binary_sensor_platform_only():
    """Only setup sensor platform."""
    with patch(
        "menuai.components.prusalink.PLATFORMS", [Platform.BINARY_SENSOR]
    ):
        yield


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_binary_sensors_no_job(
    menuai: menuai, mock_config_entry, mock_api
) -> None:
    """Test sensors while no job active."""
    assert await async_setup_component(menuai, "prusalink", {})

    state = menuai.states.get("binary_sensor.mock_title_mmu")
    assert state is not None
    assert state.state == STATE_OFF
