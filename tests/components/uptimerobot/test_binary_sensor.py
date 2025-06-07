"""Test UptimeRobot binary_sensor."""

from unittest.mock import patch

from pyuptimerobot import UptimeRobotAuthenticationException

from menuai.components.binary_sensor import BinarySensorDeviceClass
from menuai.components.uptimerobot.const import (
    ATTRIBUTION,
    COORDINATOR_UPDATE_INTERVAL,
)
from menuai.const import STATE_ON, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.util import dt as dt_util

from .common import (
    MOCK_UPTIMEROBOT_MONITOR,
    UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY,
    setup_uptimerobot_integration,
)

from tests.common import async_fire_time_changed


async def test_presentation(menuai: menuai) -> None:
    """Test the presenstation of UptimeRobot binary_sensors."""
    await setup_uptimerobot_integration(menuai)

    entity = menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY)

    assert entity.state == STATE_ON
    assert entity.attributes["device_class"] == BinarySensorDeviceClass.CONNECTIVITY
    assert entity.attributes["attribution"] == ATTRIBUTION
    assert entity.attributes["target"] == MOCK_UPTIMEROBOT_MONITOR["url"]


async def test_unavailable_on_update_failure(menuai: menuai) -> None:
    """Test entity unavailable on update failure."""
    await setup_uptimerobot_integration(menuai)

    entity = menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY)
    assert entity.state == STATE_ON

    with patch(
        "pyuptimerobot.UptimeRobot.async_get_monitors",
        side_effect=UptimeRobotAuthenticationException,
    ):
        async_fire_time_changed(menuai, dt_util.utcnow() + COORDINATOR_UPDATE_INTERVAL)
        await menuai.async_block_till_done()

    entity = menuai.states.get(UPTIMEROBOT_BINARY_SENSOR_TEST_ENTITY)
    assert entity.state == STATE_UNAVAILABLE
