"""Test the wmspro scene support."""

from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.wmspro.const import DOMAIN
from menuai.const import ATTR_ENTITY_ID, SERVICE_TURN_ON
from menuai.core import menuai
from menuai.helpers import device_registry as dr
from menuai.setup import async_setup_component

from . import setup_config_entry

from tests.common import MockConfigEntry


async def test_scene_room_device(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_hub_ping: AsyncMock,
    mock_hub_configuration_test: AsyncMock,
    mock_dest_refresh: AsyncMock,
    device_registry: dr.DeviceRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that a scene room device is created correctly."""
    assert await setup_config_entry(menuai, mock_config_entry)
    assert len(mock_hub_ping.mock_calls) == 1
    assert len(mock_hub_configuration_test.mock_calls) == 1

    device_entry = device_registry.async_get_device(identifiers={(DOMAIN, "42581")})
    assert device_entry is not None
    assert device_entry == snapshot


async def test_scene_activate(
    menuai: menuai,
    mock_config_entry: MockConfigEntry,
    mock_hub_ping: AsyncMock,
    mock_hub_configuration_test: AsyncMock,
    mock_dest_refresh: AsyncMock,
    mock_scene_call: AsyncMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that a scene entity is created and activated correctly."""
    assert await setup_config_entry(menuai, mock_config_entry)
    assert len(mock_hub_ping.mock_calls) == 1
    assert len(mock_hub_configuration_test.mock_calls) == 1

    entity = menuai.states.get("scene.raum_0_gute_nacht")
    assert entity is not None
    assert entity == snapshot

    await async_setup_component(menuai, "menuai", {})
    await menuai.services.async_call(
        "menuai",
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: entity.entity_id},
        blocking=True,
    )

    assert len(mock_scene_call.mock_calls) == 1
