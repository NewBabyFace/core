"""Sensor tests for the Google Mail integration."""

from datetime import timedelta
from unittest.mock import patch

from google.auth.exceptions import RefreshError
from httplib2 import Response
import pytest

from menuai import config_entries
from menuai.components.google_mail.const import DOMAIN
from menuai.components.sensor import SensorDeviceClass
from menuai.const import ATTR_DEVICE_CLASS, STATE_UNKNOWN
from menuai.core import menuai
from menuai.util import dt as dt_util

from .conftest import SENSOR, TOKEN, ComponentSetup

from tests.common import async_fire_time_changed, async_load_fixture


@pytest.mark.parametrize(
    ("fixture", "result"),
    [
        ("get_vacation", "2022-11-18T05:00:00+00:00"),
        ("get_vacation_no_dates", STATE_UNKNOWN),
        ("get_vacation_off", STATE_UNKNOWN),
    ],
)
async def test_sensors(
    menuai: menuai, setup_integration: ComponentSetup, fixture: str, result: str
) -> None:
    """Test we get sensor data."""
    await setup_integration()

    state = menuai.states.get(SENSOR)
    assert state.state == "2022-11-18T05:00:00+00:00"
    assert state.attributes.get(ATTR_DEVICE_CLASS) == SensorDeviceClass.TIMESTAMP

    with patch(
        "httplib2.Http.request",
        return_value=(
            Response({}),
            bytes(
                await async_load_fixture(menuai, f"{fixture}.json", DOMAIN),
                encoding="UTF-8",
            ),
        ),
    ):
        next_update = dt_util.utcnow() + timedelta(minutes=15)
        async_fire_time_changed(menuai, next_update)
        await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(SENSOR)
    assert state.state == result


async def test_sensor_reauth_trigger(
    menuai: menuai, setup_integration: ComponentSetup
) -> None:
    """Test reauth is triggered after a refresh error."""
    await setup_integration()

    with patch(TOKEN, side_effect=RefreshError):
        next_update = dt_util.utcnow() + timedelta(minutes=15)
        async_fire_time_changed(menuai, next_update)
        await menuai.async_block_till_done(wait_background_tasks=True)

    flows = menuai.config_entries.flow.async_progress()

    assert len(flows) == 1
    flow = flows[0]
    assert flow["step_id"] == "reauth_confirm"
    assert flow["handler"] == DOMAIN
    assert flow["context"]["source"] == config_entries.SOURCE_REAUTH
