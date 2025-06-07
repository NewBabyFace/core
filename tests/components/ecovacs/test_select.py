"""Tests for Ecovacs select entities."""

from deebot_client.command import Command
from deebot_client.commands.json import SetWaterInfo
from deebot_client.event_bus import EventBus
from deebot_client.events.water_info import WaterAmount, WaterAmountEvent
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components import select
from menuai.components.ecovacs.const import DOMAIN
from menuai.components.ecovacs.controller import EcovacsController
from menuai.const import (
    ATTR_ENTITY_ID,
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
    STATE_UNKNOWN,
    Platform,
)
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from .util import block_till_done

pytestmark = [pytest.mark.usefixtures("init_integration")]


@pytest.fixture
def platforms() -> Platform | list[Platform]:
    """Platforms, which should be loaded during the test."""
    return Platform.SELECT


async def notify_events(menuai: menuai, event_bus: EventBus):
    """Notify events."""
    event_bus.notify(WaterAmountEvent(WaterAmount.ULTRAHIGH))
    await block_till_done(menuai, event_bus)


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("device_fixture", "entity_ids"),
    [
        (
            "yna5x1",
            [
                "select.ozmo_950_water_flow_level",
            ],
        ),
    ],
)
async def test_selects(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    controller: EcovacsController,
    entity_ids: list[str],
) -> None:
    """Test that select entity snapshots match."""
    assert entity_ids == menuai.states.async_entity_ids()
    for entity_id in entity_ids:
        assert (state := menuai.states.get(entity_id)), f"State of {entity_id} is missing"
        assert state.state == STATE_UNKNOWN

    device = controller.devices[0]
    await notify_events(menuai, device.events)
    for entity_id in entity_ids:
        assert (state := menuai.states.get(entity_id)), f"State of {entity_id} is missing"
        assert snapshot(name=f"{entity_id}:state") == state

        assert (entity_entry := entity_registry.async_get(state.entity_id))
        assert snapshot(name=f"{entity_id}:entity-registry") == entity_entry

        assert entity_entry.device_id
        assert (device_entry := device_registry.async_get(entity_entry.device_id))
        assert device_entry.identifiers == {(DOMAIN, device.device_info["did"])}


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("device_fixture", "entity_id", "current_state", "set_state", "command"),
    [
        (
            "yna5x1",
            "select.ozmo_950_water_flow_level",
            "ultrahigh",
            "low",
            SetWaterInfo(WaterAmount.LOW),
        ),
    ],
)
async def test_selects_change(
    menuai: menuai,
    controller: EcovacsController,
    entity_id: list[str],
    current_state: str,
    set_state: str,
    command: Command,
) -> None:
    """Test that changing select entities works."""
    device = controller.devices[0]
    await notify_events(menuai, device.events)

    assert (state := menuai.states.get(entity_id)), f"State of {entity_id} is missing"
    assert state.state == current_state

    device._execute_command.reset_mock()
    await menuai.services.async_call(
        select.DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity_id, ATTR_OPTION: set_state},
        blocking=True,
    )
    device._execute_command.assert_called_with(command)
