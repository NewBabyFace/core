"""Test for the SmartThings binary_sensor platform."""

from unittest.mock import AsyncMock

from pysmartthings import Attribute, Capability
from pysmartthings.models import HealthStatus
import pytest
from syrupy.assertion import SnapshotAssertion

from menuai.components import automation, script
from menuai.components.automation import automations_with_entity
from menuai.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from menuai.components.script import scripts_with_entity
from menuai.components.smartthings import DOMAIN, MAIN
from menuai.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, Platform
from menuai.core import menuai
from menuai.helpers import entity_registry as er, issue_registry as ir
from menuai.setup import async_setup_component

from . import (
    setup_integration,
    snapshot_smartthings_entities,
    trigger_health_update,
    trigger_update,
)

from tests.common import MockConfigEntry


async def test_all_entities(
    menuai: menuai,
    snapshot: SnapshotAssertion,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test all entities."""
    await setup_integration(menuai, mock_config_entry)

    snapshot_smartthings_entities(
        menuai, entity_registry, snapshot, Platform.BINARY_SENSOR
    )


@pytest.mark.parametrize("device_fixture", ["da_ref_normal_000001"])
async def test_state_update(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test state update."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("binary_sensor.refrigerator_fridge_door").state == STATE_OFF

    await trigger_update(
        menuai,
        devices,
        "7db87911-7dce-1cf2-7119-b953432a2f09",
        Capability.CONTACT_SENSOR,
        Attribute.CONTACT,
        "open",
        component="cooler",
    )

    assert menuai.states.get("binary_sensor.refrigerator_fridge_door").state == STATE_ON


@pytest.mark.parametrize("device_fixture", ["da_ref_normal_000001"])
async def test_availability(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test availability."""
    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get("binary_sensor.refrigerator_fridge_door").state == STATE_OFF

    await trigger_health_update(
        menuai, devices, "7db87911-7dce-1cf2-7119-b953432a2f09", HealthStatus.OFFLINE
    )

    assert (
        menuai.states.get("binary_sensor.refrigerator_fridge_door").state
        == STATE_UNAVAILABLE
    )

    await trigger_health_update(
        menuai, devices, "7db87911-7dce-1cf2-7119-b953432a2f09", HealthStatus.ONLINE
    )

    assert menuai.states.get("binary_sensor.refrigerator_fridge_door").state == STATE_OFF


@pytest.mark.parametrize("device_fixture", ["da_ref_normal_000001"])
async def test_availability_at_start(
    menuai: menuai,
    unavailable_device: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test unavailable at boot."""
    await setup_integration(menuai, mock_config_entry)
    assert (
        menuai.states.get("binary_sensor.refrigerator_fridge_door").state
        == STATE_UNAVAILABLE
    )


@pytest.mark.parametrize(
    ("device_fixture", "unique_id", "suggested_object_id", "issue_string", "entity_id"),
    [
        (
            "virtual_valve",
            f"612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3_{MAIN}_{Capability.VALVE}_{Attribute.VALVE}_{Attribute.VALVE}",
            "volvo_valve",
            "valve",
            "binary_sensor.volvo_valve",
        ),
        (
            "da_ref_normal_000001",
            f"7db87911-7dce-1cf2-7119-b953432a2f09_{MAIN}_{Capability.CONTACT_SENSOR}_{Attribute.CONTACT}_{Attribute.CONTACT}",
            "refrigerator_door",
            "fridge_door",
            "binary_sensor.refrigerator_door",
        ),
    ],
)
async def test_create_issue_with_items(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    issue_registry: ir.IssueRegistry,
    unique_id: str,
    suggested_object_id: str,
    issue_string: str,
    entity_id: str,
) -> None:
    """Test we create an issue when an automation or script is using a deprecated entity."""
    issue_id = f"deprecated_binary_{issue_string}_{entity_id}"

    entity_entry = entity_registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        DOMAIN,
        unique_id,
        suggested_object_id=suggested_object_id,
        original_name=suggested_object_id,
    )

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "id": "test",
                "alias": "test",
                "trigger": {"platform": "state", "entity_id": entity_id},
                "action": {
                    "action": "automation.turn_on",
                    "target": {
                        "entity_id": "automation.test",
                    },
                },
            }
        },
    )
    assert await async_setup_component(
        menuai,
        script.DOMAIN,
        {
            script.DOMAIN: {
                "test": {
                    "sequence": [
                        {
                            "condition": "state",
                            "entity_id": entity_id,
                            "state": "on",
                        },
                    ],
                }
            }
        },
    )

    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get(entity_id).state == STATE_OFF

    assert automations_with_entity(menuai, entity_id)[0] == "automation.test"
    assert scripts_with_entity(menuai, entity_id)[0] == "script.test"

    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == f"deprecated_binary_{issue_string}_scripts"
    assert issue.translation_placeholders == {
        "entity_id": entity_id,
        "entity_name": suggested_object_id,
        "items": "- [test](/config/automation/edit/test)\n- [test](/config/script/edit/test)",
    }

    entity_registry.async_update_entity(
        entity_entry.entity_id,
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    await menuai.config_entries.async_reload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    # Assert the issue is no longer present
    assert not issue_registry.async_get_issue(DOMAIN, issue_id)


@pytest.mark.parametrize(
    ("device_fixture", "unique_id", "suggested_object_id", "issue_string", "entity_id"),
    [
        (
            "virtual_valve",
            f"612ab3c2-3bb0-48f7-b2c0-15b169cb2fc3_{MAIN}_{Capability.VALVE}_{Attribute.VALVE}_{Attribute.VALVE}",
            "volvo_valve",
            "valve",
            "binary_sensor.volvo_valve",
        ),
        (
            "da_ref_normal_000001",
            f"7db87911-7dce-1cf2-7119-b953432a2f09_{MAIN}_{Capability.CONTACT_SENSOR}_{Attribute.CONTACT}_{Attribute.CONTACT}",
            "refrigerator_door",
            "fridge_door",
            "binary_sensor.refrigerator_door",
        ),
    ],
)
async def test_create_issue(
    menuai: menuai,
    devices: AsyncMock,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    issue_registry: ir.IssueRegistry,
    unique_id: str,
    suggested_object_id: str,
    issue_string: str,
    entity_id: str,
) -> None:
    """Test we create an issue when an automation or script is using a deprecated entity."""
    issue_id = f"deprecated_binary_{issue_string}_{entity_id}"

    entity_entry = entity_registry.async_get_or_create(
        BINARY_SENSOR_DOMAIN,
        DOMAIN,
        unique_id,
        suggested_object_id=suggested_object_id,
        original_name=suggested_object_id,
    )

    await setup_integration(menuai, mock_config_entry)

    assert menuai.states.get(entity_id).state == STATE_OFF

    issue = issue_registry.async_get_issue(DOMAIN, issue_id)
    assert issue is not None
    assert issue.translation_key == f"deprecated_binary_{issue_string}"
    assert issue.translation_placeholders == {
        "entity_id": entity_id,
        "entity_name": suggested_object_id,
    }

    entity_registry.async_update_entity(
        entity_entry.entity_id,
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    await menuai.config_entries.async_reload(mock_config_entry.entry_id)
    await menuai.async_block_till_done()

    # Assert the issue is no longer present
    assert not issue_registry.async_get_issue(DOMAIN, issue_id)
