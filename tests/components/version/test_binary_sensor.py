"""The test for the version binary sensor platform."""

from __future__ import annotations

from menuai.components.version.const import DEFAULT_CONFIGURATION
from menuai.core import menuai

from .common import setup_version_integration


async def test_version_binary_sensor_local_source(menuai: menuai) -> None:
    """Test the Version binary sensor with local source."""
    await setup_version_integration(menuai)

    state = menuai.states.get("binary_sensor.local_installation_update_available")
    assert not state


async def test_version_binary_sensor(menuai: menuai) -> None:
    """Test the Version binary sensor."""
    await setup_version_integration(menuai, {**DEFAULT_CONFIGURATION, "source": "pypi"})

    state = menuai.states.get("binary_sensor.local_installation_update_available")
    assert state
