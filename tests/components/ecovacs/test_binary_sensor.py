"""Tests for Ecovacs binary sensors."""

from deebot_client.events.water_info import MopAttachedEvent
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components.ecovacs.const import DOMAIN
from menuai.components.ecovacs.controller import EcovacsController
from menuai.const import STATE_OFF, STATE_UNKNOWN, Platform
from menuai.core import menuai
from menuai.helpers import device_registry as dr, entity_registry as er

from .util import notify_and_wait

pytestmark = [pytest.mark.usefixtures("init_integration")]


@pytest.fixture
def platforms() -> Platform | list[Platform]:
    """Platforms, which should be loaded during the test."""
    return Platform.BINARY_SENSOR


async def test_mop_attached(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    controller: EcovacsController,
) -> None:
    """Test mop_attached binary sensor."""
    entity_id = "binary_sensor.ozmo_950_mop_attached"
    assert (state := menuai.states.get(entity_id))
    assert state.state == STATE_UNKNOWN

    assert (entity_entry := entity_registry.async_get(state.entity_id))
    assert entity_entry == snapshot(name=f"{entity_id}-entity_entry")
    assert entity_entry.device_id

    device = controller.devices[0]

    assert (device_entry := device_registry.async_get(entity_entry.device_id))
    assert device_entry.identifiers == {(DOMAIN, device.device_info["did"])}

    event_bus = device.events
    await notify_and_wait(menuai, event_bus, MopAttachedEvent(True))

    assert (state := menuai.states.get(state.entity_id))
    assert state == snapshot(name=f"{entity_id}-state")

    await notify_and_wait(menuai, event_bus, MopAttachedEvent(False))

    assert (state := menuai.states.get(state.entity_id))
    assert state.state == STATE_OFF
