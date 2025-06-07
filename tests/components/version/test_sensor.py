"""The test for the version sensor platform."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from pyhaversion.exceptions import HaVersionException
import pytest

from menuai.core import menuai

from .common import MOCK_VERSION, mock_get_version_update, setup_version_integration


async def test_version_sensor(menuai: menuai) -> None:
    """Test the Version sensor with different sources."""
    await setup_version_integration(menuai)

    state = menuai.states.get("sensor.local_installation")
    assert state.state == MOCK_VERSION
    assert "source" not in state.attributes
    assert "channel" not in state.attributes


async def test_update(
    menuai: menuai,
    caplog: pytest.LogCaptureFixture,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test updates."""
    await setup_version_integration(menuai)
    assert menuai.states.get("sensor.local_installation").state == MOCK_VERSION

    await mock_get_version_update(menuai, freezer, version="1970.1.1")
    assert menuai.states.get("sensor.local_installation").state == "1970.1.1"

    assert "Error fetching version data" not in caplog.text
    await mock_get_version_update(menuai, freezer, side_effect=HaVersionException)
    assert menuai.states.get("sensor.local_installation").state == "unavailable"
    assert "Error fetching version data" in caplog.text
