"""Tradfri cover (recognised as blinds in the IKEA ecosystem) platform tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytradfri.const import ATTR_REACHABLE_STATE
from pytradfri.device import Device

from menuai.components.cover import (
    ATTR_CURRENT_POSITION,
    DOMAIN as COVER_DOMAIN,
    CoverState,
)
from menuai.const import STATE_UNAVAILABLE
from menuai.core import menuai

from .common import CommandStore, setup_integration


@pytest.mark.parametrize("device", ["blind"], indirect=True)
async def test_cover_available(
    menuai: menuai,
    command_store: CommandStore,
    device: Device,
) -> None:
    """Test cover available property."""
    entity_id = "cover.test"
    await setup_integration(menuai)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 60
    assert state.attributes["model"] == "FYRTUR block-out roller blind"

    await command_store.trigger_observe_callback(
        menuai, device, {ATTR_REACHABLE_STATE: 0}
    )

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == STATE_UNAVAILABLE


@pytest.mark.parametrize("device", ["blind"], indirect=True)
@pytest.mark.parametrize(
    ("service", "service_data", "expected_state", "expected_position"),
    [
        ("set_cover_position", {"position": 100}, CoverState.OPEN, 100),
        ("set_cover_position", {"position": 0}, CoverState.CLOSED, 0),
        ("open_cover", {}, CoverState.OPEN, 100),
        ("close_cover", {}, CoverState.CLOSED, 0),
        ("stop_cover", {}, CoverState.OPEN, 60),
    ],
)
async def test_cover_services(
    menuai: menuai,
    command_store: CommandStore,
    device: Device,
    service: str,
    service_data: dict[str, Any],
    expected_state: str,
    expected_position: int,
) -> None:
    """Test cover services."""
    entity_id = "cover.test"
    await setup_integration(menuai)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == CoverState.OPEN
    assert state.attributes[ATTR_CURRENT_POSITION] == 60

    await menuai.services.async_call(
        COVER_DOMAIN,
        service,
        {"entity_id": entity_id, **service_data},
        blocking=True,
    )
    await menuai.async_block_till_done()

    await command_store.trigger_observe_callback(menuai, device)

    state = menuai.states.get(entity_id)
    assert state
    assert state.state == expected_state
    assert state.attributes[ATTR_CURRENT_POSITION] == expected_position
