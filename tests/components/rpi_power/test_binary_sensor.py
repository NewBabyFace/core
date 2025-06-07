"""Tests for rpi_power binary sensor."""

from datetime import timedelta
import logging
from unittest.mock import MagicMock

import pytest

from menuai.components.rpi_power import binary_sensor
from menuai.components.rpi_power.binary_sensor import (
    DESCRIPTION_NORMALIZED,
    DESCRIPTION_UNDER_VOLTAGE,
)
from menuai.components.rpi_power.const import DOMAIN
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed, patch

ENTITY_ID = "binary_sensor.rpi_power_status"

MODULE = "menuai.components.rpi_power.binary_sensor.new_under_voltage"


async def _async_setup_component(menuai: menuai, detected: bool) -> MagicMock:
    mocked_under_voltage = MagicMock()
    type(mocked_under_voltage).get = MagicMock(return_value=detected)
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_menuai(menuai)
    with patch(MODULE, return_value=mocked_under_voltage):
        await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
        await menuai.async_block_till_done()
    return mocked_under_voltage


async def test_new(menuai: menuai, caplog: pytest.LogCaptureFixture) -> None:
    """Test new entry."""
    await _async_setup_component(menuai, False)
    state = menuai.states.get(ENTITY_ID)
    assert state.state == STATE_OFF
    assert not any(x.levelno == logging.WARNING for x in caplog.records)


async def test_new_detected(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test new entry with under voltage detected."""
    mocked_under_voltage = await _async_setup_component(menuai, True)
    state = menuai.states.get(ENTITY_ID)
    assert state
    assert state.state == STATE_ON
    assert (
        binary_sensor.__name__,
        logging.WARNING,
        DESCRIPTION_UNDER_VOLTAGE,
    ) in caplog.record_tuples

    # back to normal
    type(mocked_under_voltage).get = MagicMock(return_value=False)
    future = dt_util.utcnow() + timedelta(minutes=1)
    async_fire_time_changed(menuai, future)
    await menuai.async_block_till_done(wait_background_tasks=True)

    state = menuai.states.get(ENTITY_ID)
    assert state
    assert state.state == STATE_OFF
    assert (
        binary_sensor.__name__,
        logging.DEBUG,
        DESCRIPTION_NORMALIZED,
    ) in caplog.record_tuples
