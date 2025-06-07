"""The tests for Netatmo cover."""

from unittest.mock import AsyncMock, patch

from syrupy.assertion import SnapshotAssertion

from menuai.components.cover import (
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import selected_platforms, snapshot_platform_entities

from tests.common import MockConfigEntry


async def test_entity(
    menuai: menuai,
    config_entry: MockConfigEntry,
    netatmo_auth: AsyncMock,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test entities."""
    await snapshot_platform_entities(
        menuai,
        config_entry,
        Platform.COVER,
        entity_registry,
        snapshot,
    )


async def test_cover_setup_and_services(
    menuai: menuai, config_entry: MockConfigEntry, netatmo_auth: AsyncMock
) -> None:
    """Test setup and services."""
    with selected_platforms([Platform.COVER]):
        assert await menuai.config_entries.async_setup(config_entry.entry_id)

        await menuai.async_block_till_done()

    switch_entity = "cover.entrance_blinds"

    assert menuai.states.get(switch_entity).state == "closed"

    # Test cover open
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_OPEN_COVER,
            {ATTR_ENTITY_ID: switch_entity},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {
                "modules": [
                    {
                        "id": "0009999992",
                        "target_position": 100,
                        "bridge": "12:34:56:30:d5:d4",
                    }
                ]
            }
        )

    # Test cover close
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_CLOSE_COVER,
            {ATTR_ENTITY_ID: switch_entity},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {
                "modules": [
                    {
                        "id": "0009999992",
                        "target_position": 0,
                        "bridge": "12:34:56:30:d5:d4",
                    }
                ]
            }
        )

    # Test stop cover
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_STOP_COVER,
            {ATTR_ENTITY_ID: switch_entity},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {
                "modules": [
                    {
                        "id": "0009999992",
                        "target_position": -1,
                        "bridge": "12:34:56:30:d5:d4",
                    }
                ]
            }
        )

    # Test set cover position
    with patch("pyatmo.home.Home.async_set_state") as mock_set_state:
        await menuai.services.async_call(
            COVER_DOMAIN,
            SERVICE_SET_COVER_POSITION,
            {ATTR_ENTITY_ID: switch_entity, ATTR_POSITION: 50},
            blocking=True,
        )
        await menuai.async_block_till_done()
        mock_set_state.assert_called_once_with(
            {
                "modules": [
                    {
                        "id": "0009999992",
                        "target_position": 50,
                        "bridge": "12:34:56:30:d5:d4",
                    }
                ]
            }
        )
