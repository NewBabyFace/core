"""The test for the sensibo coordinator."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from pysensibo.exceptions import AuthenticationError, SensiboError
from pysensibo.model import SensiboData
import pytest

from menuai.components.climate import HVACMode
from menuai.components.sensibo.const import DOMAIN
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from . import ENTRY_CONFIG

from tests.common import MockConfigEntry, async_fire_time_changed


async def test_coordinator(
    menuai: menuai,
    mock_client: MagicMock,
    get_data: tuple[SensiboData, dict[str, Any], dict[str, Any]],
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test the Sensibo coordinator with errors."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=ENTRY_CONFIG,
        entry_id="1",
        unique_id="firstnamelastname",
        version=2,
    )

    config_entry.add_to_menuai(menuai)

    mock_client.async_get_devices_data.return_value.parsed[
        "ABC999111"
    ].hvac_mode = "heat"
    mock_client.async_get_devices_data.return_value.parsed["ABC999111"].device_on = True

    mock_data = mock_client.async_get_devices_data
    mock_data.return_value = get_data[0]
    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()
    mock_data.assert_called_once()
    state = menuai.states.get("climate.hallway")
    assert state.state == HVACMode.HEAT
    mock_data.reset_mock()

    mock_data.side_effect = SensiboError("info")
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    mock_data.assert_called_once()
    state = menuai.states.get("climate.hallway")
    assert state.state == STATE_UNAVAILABLE
    mock_data.reset_mock()

    mock_data.return_value = SensiboData(raw={}, parsed={})
    mock_data.side_effect = None
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    mock_data.assert_called_once()
    state = menuai.states.get("climate.hallway")
    assert state.state == STATE_UNAVAILABLE
    mock_data.reset_mock()

    mock_data.return_value = get_data[0]
    mock_data.side_effect = None
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    mock_data.assert_called_once()
    state = menuai.states.get("climate.hallway")
    assert state.state == HVACMode.HEAT
    mock_data.reset_mock()

    mock_data.side_effect = AuthenticationError("info")
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()
    mock_data.assert_called_once()
    state = menuai.states.get("climate.hallway")
    assert state.state == STATE_UNAVAILABLE

    assert "Platform sensibo does not generate unique IDs" not in caplog.text
