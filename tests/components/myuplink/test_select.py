"""Tests for myuplink select module."""

from unittest.mock import MagicMock

from aiohttp import ClientError
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
    Platform,
)
from menuai.core import menuai
from menuai.exceptions import menuaiError
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry, snapshot_platform

TEST_PLATFORM = Platform.SELECT
pytestmark = pytest.mark.parametrize("platforms", [(TEST_PLATFORM,)])

ENTITY_ID = "select.gotham_city_comfort_mode"
ENTITY_FRIENDLY_NAME = "Gotham City comfort mode"
ENTITY_UID = "robin-r-1234-20240201-123456-aa-bb-cc-dd-ee-ff-47041"


async def test_selecting(
    menuai: menuai,
    mock_myuplink_client: MagicMock,
    setup_platform: None,
) -> None:
    """Test select option service."""

    await menuai.services.async_call(
        TEST_PLATFORM,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "Economy"},
        blocking=True,
    )
    await menuai.async_block_till_done()
    mock_myuplink_client.async_set_device_points.assert_called_once()

    # Test handling of exception from API.

    mock_myuplink_client.async_set_device_points.side_effect = ClientError
    with pytest.raises(menuaiError):
        await menuai.services.async_call(
            TEST_PLATFORM,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_OPTION: "Economy"},
            blocking=True,
        )
    assert mock_myuplink_client.async_set_device_points.call_count == 2


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

    entry = entity_registry.async_get("select.gotham_city_all")
    assert entry.unique_id == "robin-r-1234-20240201-123456-aa-bb-cc-dd-ee-ff-47660"


async def test_select_states(
    menuai: menuai,
    mock_myuplink_client: MagicMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
    entity_registry: er.EntityRegistry,
    setup_platform: None,
) -> None:
    """Test select entity state."""

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)
