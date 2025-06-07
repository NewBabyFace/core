"""Tests for Shelly valve platform."""

from unittest.mock import Mock

from aioshelly.const import MODEL_GAS
import pytest

from menuai.components.valve import DOMAIN as VALVE_DOMAIN, ValveState
from menuai.const import ATTR_ENTITY_ID, SERVICE_CLOSE_VALVE, SERVICE_OPEN_VALVE
from menuai.core import menuai
from menuai.helpers.entity_registry import EntityRegistry

from . import init_integration

GAS_VALVE_BLOCK_ID = 6


async def test_block_device_gas_valve(
    menuai: menuai,
    entity_registry: EntityRegistry,
    mock_block_device: Mock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test block device Shelly Gas with Valve addon."""
    await init_integration(menuai, 1, MODEL_GAS)
    entity_id = "valve.test_name_valve"

    assert (entry := entity_registry.async_get(entity_id))
    assert entry.unique_id == "123456789ABC-valve_0-valve"

    assert (state := menuai.states.get(entity_id))
    assert state.state == ValveState.CLOSED

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_OPEN_VALVE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert (state := menuai.states.get(entity_id))
    assert state.state == ValveState.OPENING

    monkeypatch.setattr(mock_block_device.blocks[GAS_VALVE_BLOCK_ID], "valve", "opened")
    mock_block_device.mock_update()
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == ValveState.OPEN

    await menuai.services.async_call(
        VALVE_DOMAIN,
        SERVICE_CLOSE_VALVE,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )

    assert (state := menuai.states.get(entity_id))
    assert state.state == ValveState.CLOSING

    monkeypatch.setattr(mock_block_device.blocks[GAS_VALVE_BLOCK_ID], "valve", "closed")
    mock_block_device.mock_update()
    await menuai.async_block_till_done()

    assert (state := menuai.states.get(entity_id))
    assert state.state == ValveState.CLOSED
