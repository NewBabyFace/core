"""The tests for the Ring number platform."""

from unittest.mock import Mock

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from menuai.const import ATTR_ENTITY_ID, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .common import MockConfigEntry, async_check_entity_translations, setup_platform

from tests.common import snapshot_platform


@pytest.mark.parametrize(
    ("entity_id", "unique_id"),
    [
        ("number.downstairs_volume", "123456-volume"),
        ("number.front_door_volume", "987654-volume"),
        ("number.ingress_doorbell_volume", "185036587-doorbell_volume"),
        ("number.ingress_mic_volume", "185036587-mic_volume"),
        ("number.ingress_voice_volume", "185036587-voice_volume"),
    ],
)
async def test_entity_registry(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    mock_ring_client: Mock,
    entity_id: str,
    unique_id: str,
) -> None:
    """Tests that the devices are registered in the entity registry."""
    await setup_platform(menuai, Platform.NUMBER)

    entry = entity_registry.async_get(entity_id)
    assert entry is not None and entry.unique_id == unique_id


async def test_states(
    menuai: menuai,
    mock_ring_client: Mock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test states."""

    mock_config_entry.add_to_menuai(menuai)
    await setup_platform(menuai, Platform.NUMBER)
    await async_check_entity_translations(
        menuai, entity_registry, mock_config_entry.entry_id, NUMBER_DOMAIN
    )
    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


@pytest.mark.parametrize(
    ("entity_id", "new_value"),
    [
        ("number.downstairs_volume", "4.0"),
        ("number.front_door_volume", "3.0"),
        ("number.ingress_doorbell_volume", "7.0"),
        ("number.ingress_mic_volume", "2.0"),
        ("number.ingress_voice_volume", "5.0"),
    ],
)
async def test_volume_can_be_changed(
    menuai: menuai,
    mock_ring_client: Mock,
    entity_id: str,
    new_value: str,
) -> None:
    """Tests the volume can be changed correctly."""
    await setup_platform(menuai, Platform.NUMBER)

    state = menuai.states.get(entity_id)
    assert state is not None
    old_value = state.state

    # otherwise this test would be pointless
    assert old_value != new_value

    await menuai.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: new_value},
        blocking=True,
    )

    await menuai.async_block_till_done()
    state = menuai.states.get(entity_id)
    assert state is not None and state.state == new_value
