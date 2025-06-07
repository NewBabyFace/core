"""Tests for the SmartThings integration."""

from typing import Any
from unittest.mock import AsyncMock

from pysmartthings import Attribute, Capability, DeviceEvent, DeviceHealthEvent
from pysmartthings.models import HealthStatus
from syrupy.assertion import SnapshotAssertion

from menuai.components.smartthings.const import MAIN
from menuai.const import Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def setup_integration(menuai: menuai, config_entry: MockConfigEntry) -> None:
    """Fixture for setting up the component."""
    config_entry.add_to_menuai(menuai)

    await menuai.config_entries.async_setup(config_entry.entry_id)
    await menuai.async_block_till_done()


def snapshot_smartthings_entities(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    platform: Platform,
) -> None:
    """Snapshot SmartThings entities."""
    entities = menuai.states.async_all(platform)
    for entity_state in entities:
        entity_entry = entity_registry.async_get(entity_state.entity_id)
        assert entity_entry == snapshot(name=f"{entity_entry.entity_id}-entry")
        assert entity_state == snapshot(name=f"{entity_entry.entity_id}-state")


def set_attribute_value(
    mock: AsyncMock,
    capability: Capability,
    attribute: Attribute,
    value: Any,
    component: str = MAIN,
) -> None:
    """Set the value of an attribute."""
    mock.get_device_status.return_value[component][capability][attribute].value = value


async def trigger_update(
    menuai: menuai,
    mock: AsyncMock,
    device_id: str,
    capability: Capability,
    attribute: Attribute,
    value: str | float | dict[str, Any] | list[Any] | None,
    data: dict[str, Any] | None = None,
    component: str = MAIN,
) -> None:
    """Trigger an update."""
    event = DeviceEvent(
        "abc",
        "abc",
        "abc",
        device_id,
        component,
        capability,
        attribute,
        value,
        data,
    )
    for call in mock.add_unspecified_device_event_listener.call_args_list:
        call[0][0](event)
    for call in mock.add_device_event_listener.call_args_list:
        if call[0][0] == device_id:
            call[0][3](event)
    for call in mock.add_device_capability_event_listener.call_args_list:
        if call[0][0] == device_id and call[0][2] == capability:
            call[0][3](event)
    await menuai.async_block_till_done()


async def trigger_health_update(
    menuai: menuai, mock: AsyncMock, device_id: str, status: HealthStatus
) -> None:
    """Trigger a health update."""
    event = DeviceHealthEvent("abc", "abc", status)
    for call in mock.add_device_availability_event_listener.call_args_list:
        if call[0][0] == device_id:
            call[0][1](event)
    await menuai.async_block_till_done()
