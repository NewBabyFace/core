"""Tests for the Niko Home Control cover platform."""

from unittest.mock import AsyncMock, patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.cover import DOMAIN as COVER_DOMAIN
from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    STATE_CLOSED,
    STATE_OPEN,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from . import find_update_callback, setup_integration

from tests.common import MockConfigEntry, snapshot_platform


async def test_cover(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    mock_niko_home_control_connection: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    with patch(
        "menuai.components.niko_home_control.PLATFORMS", [Platform.COVER]
    ):
        await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("cover_id", "entity_id"),
    [
        (0, "cover.cover"),
    ],
)
async def test_open_cover(
    menuai: menuai,
    mock_niko_home_control_connection: AsyncMock,
    mock_config_entry: MockConfigEntry,
    cover_id: int,
    entity_id: int,
) -> None:
    """Test opening the cover."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_niko_home_control_connection.covers[cover_id].open.assert_called_once_with()


@pytest.mark.parametrize(
    ("cover_id", "entity_id"),
    [
        (0, "cover.cover"),
    ],
)
async def test_close_cover(
    menuai: menuai,
    mock_niko_home_control_connection: AsyncMock,
    mock_config_entry: MockConfigEntry,
    cover_id: int,
    entity_id: str,
) -> None:
    """Test closing the cover."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_niko_home_control_connection.covers[cover_id].close.assert_called_once_with()


@pytest.mark.parametrize(
    ("cover_id", "entity_id"),
    [
        (0, "cover.cover"),
    ],
)
async def test_stop_cover(
    menuai: menuai,
    mock_niko_home_control_connection: AsyncMock,
    mock_config_entry: MockConfigEntry,
    cover_id: int,
    entity_id: str,
) -> None:
    """Test closing the cover."""
    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_STOP_COVER,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    mock_niko_home_control_connection.covers[cover_id].stop.assert_called_once_with()


async def test_updating(
    menuai: menuai,
    mock_niko_home_control_connection: AsyncMock,
    mock_config_entry: MockConfigEntry,
    cover: AsyncMock,
) -> None:
    """Test closing the cover."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("cover.cover").state == STATE_OPEN

    cover.state = 0
    await find_update_callback(mock_niko_home_control_connection, 3)(0)
    await menuai.async_block_till_done()

    assert menuai.states.get("cover.cover").state == STATE_CLOSED

    cover.state = 100
    await find_update_callback(mock_niko_home_control_connection, 3)(100)
    await menuai.async_block_till_done()

    assert menuai.states.get("cover.cover").state == STATE_OPEN
