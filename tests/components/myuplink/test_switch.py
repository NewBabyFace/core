"""Tests for myuplink switch module."""

from unittest.mock import MagicMock

from aiohttp import ClientError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform

TEST_PLATFORM = Platform.SWITCH
pytestmark = pytest.mark.parametrize("platforms", [(TEST_PLATFORM,)])

ENTITY_ID = "switch.gotham_city_temporary_lux"
ENTITY_FRIENDLY_NAME = "Gotham City Tempo\xadrary lux"
ENTITY_UID = "robin-r-1234-20240201-123456-aa-bb-cc-dd-ee-ff-50004"


async def test_entity_registry(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_myuplink_client: MagicMock,
    setup_platform: None,
) -> None:
    """Test that the entities are registered in the entity registry."""

    entry = entity_registry.async_get(ENTITY_ID)
    assert entry.unique_id == ENTITY_UID


@pytest.mark.parametrize(
    ("service"),
    [
        (SERVICE_TURN_ON),
        (SERVICE_TURN_OFF),
    ],
)
async def test_switching(
    menuai: menuai,
    mock_myuplink_client: MagicMock,
    setup_platform: None,
    service: str,
) -> None:
    """Test the switch can be turned on/off."""

    await menuai.services.async_call(
        TEST_PLATFORM, service, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    await menuai.async_block_till_done()
    mock_myuplink_client.async_set_device_points.assert_called_once()


@pytest.mark.parametrize(
    ("service"),
    [
        (SERVICE_TURN_ON),
        (SERVICE_TURN_OFF),
    ],
)
async def test_api_failure(
    menuai: menuai,
    mock_myuplink_client: MagicMock,
    setup_platform: None,
    service: str,
) -> None:
    """Test handling of exception from API."""
    mock_myuplink_client.async_set_device_points.side_effect = ClientError

    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            TEST_PLATFORM, service, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
        )
    mock_myuplink_client.async_set_device_points.assert_called_once()


@pytest.mark.parametrize(
    "load_device_points_file",
    ["device_points_nibe_smo20.json"],
)
async def test_entity_registry_smo20(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_myuplink_client: MagicMock,
    setup_platform: None,
) -> None:
    """Test that the entities are registered in the entity registry."""

    entry = entity_registry.async_get(ENTITY_ID)
    assert entry.unique_id == ENTITY_UID


async def test_switch_states(
    menuai: menuai,
    mock_myuplink_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    setup_platform: None,
) -> None:
    """Test switch entity state."""

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
