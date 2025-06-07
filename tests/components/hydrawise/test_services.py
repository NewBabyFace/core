"""Test Hydrawise services."""

from datetime import datetime
from unittest.mock import AsyncMock

from pydrawise.schema import Zone

from menuai.components.hydrawise.const import (
    ATTR_DURATION,
    ATTR_UNTIL,
    DOMAIN,
    SERVICE_RESUME,
    SERVICE_START_WATERING,
    SERVICE_SUSPEND,
)
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from tests.common import MockConfigEntry


async def test_start_watering(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pydrawise: AsyncMock,
    zones: list[Zone],
) -> None:
    """Test that the start_watering service works as intended."""
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_START_WATERING,
        {
            ATTR_ENTITY_ID: "binary_sensor.zone_one_watering",
            ATTR_DURATION: 20,
        },
        blocking=True,
    )
    mock_pydrawise.start_zone.assert_called_once_with(
        zones[0], custom_run_duration=20 * 60
    )


async def test_start_watering_no_duration(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pydrawise: AsyncMock,
    zones: list[Zone],
) -> None:
    """Test that the start_watering service works with no duration specified."""
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_START_WATERING,
        {ATTR_ENTITY_ID: "binary_sensor.zone_one_watering"},
        blocking=True,
    )
    mock_pydrawise.start_zone.assert_called_once_with(zones[0], custom_run_duration=0)


async def test_resume(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pydrawise: AsyncMock,
    zones: list[Zone],
) -> None:
    """Test that the resume service works as intended."""
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_RESUME,
        {ATTR_ENTITY_ID: "binary_sensor.zone_one_watering"},
        blocking=True,
    )
    mock_pydrawise.resume_zone.assert_called_once_with(zones[0])


async def test_suspend(
    menuai: menuai,
    mock_added_config_entry: MockConfigEntry,
    mock_pydrawise: AsyncMock,
    zones: list[Zone],
) -> None:
    """Test that the suspend service works as intended."""
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SUSPEND,
        {
            ATTR_ENTITY_ID: "binary_sensor.zone_one_watering",
            ATTR_UNTIL: datetime(2026, 1, 1, 0, 0, 0),
        },
        blocking=True,
    )
    mock_pydrawise.suspend_zone.assert_called_once_with(
        zones[0], until=datetime(2026, 1, 1, 0, 0, 0)
    )
