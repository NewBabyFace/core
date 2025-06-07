"""Test the MenuAI analytics sensor module."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from python_menuai_analytics import (
    menuaiAnalyticsConnectionError,
    menuaiAnalyticsNotModifiedError,
)
from syrupy.assertion import SnapshotAssertion

from menuai.const import STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch(
        "menuai.components.analytics_insights.PLATFORMS",
        [Platform.SENSOR],
    ):
        await setup_integration(menuai, mock_config_entry)
        await snapshot_platform(
            menuai, entity_registry, snapshot, mock_config_entry.entry_id
        )


async def test_connection_error(
    menuai: menuai,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test connection error."""
    await setup_integration(menuai, mock_config_entry)

    mock_analytics_client.get_current_analytics.side_effect = (
        menuaiAnalyticsConnectionError()
    )
    freezer.tick(delta=timedelta(hours=12))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    assert (
        menuai.states.get("sensor.menuai_analytics_spotify").state
        == STATE_UNAVAILABLE
    )


async def test_data_not_modified(
    menuai: menuai,
    mock_analytics_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test not updating data if its not modified."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("sensor.menuai_analytics_spotify").state == "24388"
    mock_analytics_client.get_current_analytics.side_effect = (
        menuaiAnalyticsNotModifiedError
    )
    freezer.tick(delta=timedelta(hours=12))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    mock_analytics_client.get_current_analytics.assert_called()
    assert menuai.states.get("sensor.menuai_analytics_spotify").state == "24388"
