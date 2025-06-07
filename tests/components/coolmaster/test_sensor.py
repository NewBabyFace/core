"""The test for the Coolmaster sensor platform."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def test_sensor(
    menuai: menuai,
    load_int: ConfigEntry,
) -> None:
    """Test the Coolmaster sensor."""
    assert menuai.states.get("sensor.l1_100_error_code").state == "OK"
    assert menuai.states.get("sensor.l1_101_error_code").state == "Err1"
