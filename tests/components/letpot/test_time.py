"""Test time entities for the LetPot integration."""

from datetime import time
from unittest.mock import MagicMock, patch

from letpot.exceptions import LetPotConnectionException, LetPotException
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.time import SERVICE_SET_VALUE
from menuai.const import Platform
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_client: MagicMock,
    mock_device_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test time entities."""
    with patch("menuai.components.letpot.PLATFORMS", [Platform.TIME]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_set_time(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    mock_device_client: MagicMock,
) -> None:
    """Test setting the time entity."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        "time",
        SERVICE_SET_VALUE,
        service_data={"time": time(hour=7, minute=0)},
        blocking=True,
        target={"entity_id": "time.garden_light_on"},
    )

    mock_device_client.set_light_schedule.assert_awaited_once_with(time(7, 0), None)


@pytest.mark.parametrize(
    ("exception", "user_error"),
    [
        (
            LetPotConnectionException("Connection failed"),
            "An error occurred while communicating with the LetPot device: Connection failed",
        ),
        (
            LetPotException("Random thing failed"),
            "An unknown error occurred while communicating with the LetPot device: Random thing failed",
        ),
    ],
)
async def test_time_error(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
    mock_device_client: MagicMock,
    exception: Exception,
    user_error: str,
) -> None:
    """Test time entity exception handling."""
    await setup_integration(menuai, mock_config_entry)

    mock_device_client.set_light_schedule.side_effect = exception

    assert menuai.states.get("time.garden_light_on") is not None
    with pytest.raises(menuaiError, match=user_error):
        await menuai.services.async_call(
            "time",
            SERVICE_SET_VALUE,
            service_data={"time": time(hour=7, minute=0)},
            blocking=True,
            target={"entity_id": "time.garden_light_on"},
        )
