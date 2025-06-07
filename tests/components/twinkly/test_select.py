"""Tests for the Twinkly select component."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.select import DOMAIN as SELECT_DOMAIN
from menuai.const import ATTR_ENTITY_ID, ATTR_OPTION, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed, snapshot_platform


@pytest.mark.usefixtures("mock_twinkly_client")
async def test_select_entities(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the created select entities."""
    with patch("menuai.components.twinkly.PLATFORMS", [Platform.SELECT]):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_select_mode(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_twinkly_client: AsyncMock,
) -> None:
    """Test selecting a mode."""
    await setup_integration(menuai, mock_config_entry)

    state = menuai.states.get("select.tree_1_mode")
    assert state is not None
    assert state.state == "color"

    await menuai.services.async_call(
        SELECT_DOMAIN,
        "select_option",
        {
            ATTR_ENTITY_ID: "select.tree_1_mode",
            ATTR_OPTION: "movie",
        },
        blocking=True,
    )

    mock_twinkly_client.set_mode.assert_called_once_with("movie")
    mock_twinkly_client.interview.assert_not_called()


async def test_mode_unavailable(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_twinkly_client: AsyncMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test handling of unavailable mode data."""
    await setup_integration(menuai, mock_config_entry)

    mock_twinkly_client.get_mode.side_effect = Exception
    freezer.tick(timedelta(seconds=30))
    async_fire_time_changed(menuai)
    await menuai.async_block_till_done()

    state = menuai.states.get("select.tree_1_mode")
    assert state.state == STATE_UNAVAILABLE
