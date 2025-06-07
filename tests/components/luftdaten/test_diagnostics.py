"""Tests for the diagnostics data provided by the Sensor.Community integration."""

from menuai.components.diagnostics import REDACTED
from menuai.core import menuai

from tests.common import MockConfigEntry
from tests.components.diagnostics import get_diagnostics_for_config_entry
from tests.typing import ClientSessionGenerator


async def test_diagnostics(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
) -> None:
    """Test diagnostics."""
    assert await get_diagnostics_for_config_entry(
        menuai, menuai_client, init_integration
    ) == {
        "P1": 8.5,
        "P2": 4.07,
        "altitude": 123.456,
        "humidity": 34.7,
        "latitude": REDACTED,
        "longitude": REDACTED,
        "pressure": 98545.0,
        "pressure_at_sealevel": 103102.13,
        "sensor_id": REDACTED,
        "temperature": 22.3,
    }
