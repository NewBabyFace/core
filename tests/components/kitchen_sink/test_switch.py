"""The tests for the demo switch component."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.kitchen_sink import DOMAIN
from menuai.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from menuai.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

SWITCH_ENTITY_IDS = ["switch.outlet_1", "switch.outlet_2"]


@pytest.fixture
def switch_only() -> Generator[None]:
    """Enable only the switch platform."""
    with patch(
        "menuai.components.kitchen_sink.COMPONENTS_WITH_DEMO_PLATFORM",
        [Platform.SWITCH],
    ):
        yield


@pytest.fixture(autouse=True)
async def setup_comp(menuai: menuai, switch_only: None) -> None:
    """Set up demo component."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {}})
    await menuai.async_block_till_done()


async def test_state(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test switch state."""
    for entity_id in SWITCH_ENTITY_IDS:
        state = menuai.states.get(entity_id)
        assert state == snapshot
        entity_entry = entity_registry.async_get(entity_id)
        assert entity_entry == snapshot
        sub_device_entry = device_registry.async_get(entity_entry.device_id)
        assert sub_device_entry == snapshot
        main_device_entry = device_registry.async_get(sub_device_entry.via_device_id)
        assert main_device_entry == snapshot


@pytest.mark.parametrize("switch_entity_id", SWITCH_ENTITY_IDS)
async def test_turn_on(menuai: menuai, switch_entity_id: str) -> None:
    """Test switch turn on method."""
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_OFF

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_ON


@pytest.mark.parametrize("switch_entity_id", SWITCH_ENTITY_IDS)
async def test_turn_off(menuai: menuai, switch_entity_id: str) -> None:
    """Test switch turn off method."""
    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_ON

    await menuai.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: switch_entity_id},
        blocking=True,
    )

    state = menuai.states.get(switch_entity_id)
    assert state.state == STATE_OFF
