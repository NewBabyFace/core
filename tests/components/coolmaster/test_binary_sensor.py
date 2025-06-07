"""The test for the Coolmaster binary sensor platform."""

from __future__ import annotations

from menuai.config_entries import ConfigEntry
from menuai.core import menuai


async def test_binary_sensor(
    menuai: menuai,
    load_int: ConfigEntry,
) -> None:
    """Test the Coolmaster binary sensor."""
    assert menuai.states.get("binary_sensor.l1_100_clean_filter").state == "off"
    assert menuai.states.get("binary_sensor.l1_101_clean_filter").state == "on"
