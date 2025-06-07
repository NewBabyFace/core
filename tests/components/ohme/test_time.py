"""Tests for time."""

from unittest.mock import MagicMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.time import (
    ATTR_TIME,
    DOMAIN as TIME_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_time(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the Ohme sensors."""
    with patch("menuai.components.ohme.PLATFORMS", [Platform.TIME]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_set_time(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_client: MagicMock,
) -> None:
    """Test the time set."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        TIME_DOMAIN,
        SERVICE_SET_VALUE,
        service_data={
            ATTR_TIME: "00:00:00",
        },
        target={
            ATTR_ENTITY_ID: "time.ohme_home_pro_target_time",
        },
        blocking=True,
    )

    assert len(mock_client.async_set_target.mock_calls) == 1
