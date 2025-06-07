"""Test the Chacon Dio cover."""

from collections.abc import Callable
from unittest.mock import AsyncMock

from syrupy.assertion import SnapshotAssertion

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
    CoverState,
)
from menuai.components.menuai import SERVICE_UPDATE_ENTITY
from menuai.const import ATTR_ENTITY_ID
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from . import setup_integration

from tests.common import MockConfigEntry, snapshot_platform

COVER_ENTITY_ID = "cover.shutter_mock_1"


async def test_entities(
    menuai: menuai,
    mock_dio_chacon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the creation and values of the Chacon Dio covers."""

    await setup_integration(menuai, mock_config_entry)

    await snapshot_platform(menuai, entity_registry, snapshot, mock_config_entry.entry_id)


async def test_update(
    menuai: menuai,
    mock_dio_chacon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the creation and values of the Chacon Dio covers."""

    await setup_integration(menuai, mock_config_entry)

    mock_dio_chacon_client.get_status_details.return_value = {
        "L4HActuator_idmock1": {
            "id": "L4HActuator_idmock1",
            "connected": True,
            "openlevel": 51,
            "movement": "stop",
        }
    }

    await async_setup_component(menuai, menuai_DOMAIN, {})
    await menuai.services.async_call(
        menuai_DOMAIN,
        SERVICE_UPDATE_ENTITY,
        {ATTR_ENTITY_ID: COVER_ENTITY_ID},
        blocking=True,
    )

    state = menuai.states.get(COVER_ENTITY_ID)
    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 51
    assert state.state == CoverState.OPEN


async def test_cover_actions(
    menuai: menuai,
    mock_dio_chacon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the creation and values of the Chacon Dio covers."""

    await setup_integration(menuai, mock_config_entry)

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: COVER_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(COVER_ENTITY_ID)
    assert state.state == CoverState.CLOSING

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_STOP_COVER,
        {ATTR_ENTITY_ID: COVER_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(COVER_ENTITY_ID)
    assert state.state == CoverState.OPEN

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: COVER_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(COVER_ENTITY_ID)
    assert state.state == CoverState.OPENING

    await menuai.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_POSITION: 25, ATTR_ENTITY_ID: COVER_ENTITY_ID},
        blocking=True,
    )
    await menuai.async_block_till_done()
    state = menuai.states.get(COVER_ENTITY_ID)
    assert state.state == CoverState.OPENING


async def test_cover_callbacks(
    menuai: menuai,
    mock_dio_chacon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the callbacks on the Chacon Dio covers."""

    await setup_integration(menuai, mock_config_entry)

    # Server side callback tests
    # We find the callback method on the mock client
    callback_device_state_function: Callable = (
        mock_dio_chacon_client.set_callback_device_state_by_device.call_args[0][1]
    )

    # Define a method to simply call it
    async def _callback_device_state_function(open_level: int, movement: str) -> None:
        callback_device_state_function(
            {
                "id": "L4HActuator_idmock1",
                "connected": True,
                "openlevel": open_level,
                "movement": movement,
            }
        )
        await menuai.async_block_till_done()

    # And call it to effectively launch the callback as the server would do
    await _callback_device_state_function(79, "stop")
    state = menuai.states.get(COVER_ENTITY_ID)
    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 79
    assert state.state == CoverState.OPEN

    await _callback_device_state_function(90, "up")
    state = menuai.states.get(COVER_ENTITY_ID)
    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 90
    assert state.state == CoverState.OPENING

    await _callback_device_state_function(60, "down")
    state = menuai.states.get(COVER_ENTITY_ID)
    assert state
    assert state.attributes.get(ATTR_CURRENT_POSITION) == 60
    assert state.state == CoverState.CLOSING


async def test_no_cover_found(
    menuai: menuai,
    mock_dio_chacon_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test the cover absence."""

    mock_dio_chacon_client.search_all_devices.return_value = None

    await setup_integration(menuai, mock_config_entry)

    assert not menuai.states.get(COVER_ENTITY_ID)
