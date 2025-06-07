"""Tests for the Cambridge Audio switch platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.switch import DOMAIN as SWITCH_DOMAIN, SERVICE_TURN_ON
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_stream_magic_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch("menuai.components.cambridge_audio.PLATFORMS", [Platform.SWITCH]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_setting_value(
    menuai: menuai,
    mock_stream_magic_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setting value."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {
            ATTR_ENTITY_ID: "switch.cambridge_audio_cxnv2_early_update",
        },
        blocking=True,
    )
    mock_stream_magic_client.set_early_update.assert_called_once_with(True)
    mock_stream_magic_client.set_early_update.reset_mock()

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {
            ATTR_ENTITY_ID: "switch.cambridge_audio_cxnv2_early_update",
        },
        blocking=True,
    )
    mock_stream_magic_client.set_early_update.assert_called_once_with(False)
