"""The test for the sensibo sensor."""

from __future__ import annotations

from unittest.mock import Mock

from yalesmartalarmclient import YaleSmartAlarmData

from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_coordinator_setup_and_update_errors(
    menuai: menuai,
    load_config_entry: tuple[MockConfigEntry, Mock],
    get_data: YaleSmartAlarmData,
) -> None:
    """Test the Yale Smart Living coordinator with errors."""

    state = menuai.states.get("sensor.smoke_alarm_temperature")
    assert state.state == "21"
