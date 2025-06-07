"""Tests for OneDrive sensors."""

from datetime import timedelta
from typing import Any
from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory
from onedrive_personal_sdk.const import DriveType
from onedrive_personal_sdk.exceptions import HttpRequestException
from onedrive_personal_sdk.models.items import Drive
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sensors(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the OneDrive sensors."""

    await setup_integration(menuai, mock_config_entry)
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("attr", "side_effect"),
    [
        ("side_effect", HttpRequestException(503, "Service Unavailable")),
        ("return_value", Drive(id="id", name="name", drive_type=DriveType.PERSONAL)),
    ],
)
async def test_update_failure(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_onedrive_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    attr: str,
    side_effect: Any,
) -> None:
    """Ensure sensors are going unavailable on update failure."""
    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("sensor.my_drive_remaining_storage")
    assert state.state == "0.75"

    setattr(mock_onedrive_client.get_drive, attr, side_effect)

    freezer.tick(timedelta(minutes=10))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("sensor.my_drive_remaining_storage")
    assert state.state == STATE_UNAVAILABLE
