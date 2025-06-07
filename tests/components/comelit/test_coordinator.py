"""Tests for Comelit SimpleHome coordinator."""

from unittest.mock import AsyncMock

from aiocomelit.exceptions import CannotAuthenticate, CannotConnect, CannotRetrieveData
from freezegun.api import FrozenDateTimeFactory
import pytest

from menuai.components.comelit.const import SCAN_INTERVAL
from menuai.const import STATE_OFF, STATE_UNAVAILABLE
from menuai.core import menuai

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed


@pytest.mark.parametrize(
    "side_effect",
    [
        CannotConnect,
        CannotRetrieveData,
        CannotAuthenticate,
    ],
)
async def test_coordinator_data_update_fails(
    menuai: menuai,
    freezer: FrozenDateTimeFactory,
    mock_serial_bridge: AsyncMock,
    mock_serial_bridge_config_entry: MockConfigEntry,
    side_effect: Exception,
) -> None:
    """Test coordinator data update exceptions."""

    entity_id = "light.light0"

    await setup_integration(menuai, mock_serial_bridge_config_entry)

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_OFF

    mock_serial_bridge.login.side_effect = side_effect

    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNAVAILABLE
