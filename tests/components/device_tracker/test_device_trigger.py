"""The tests for Device Tracker device triggers."""

import pytest
from pytest_unordered import unordered
import voluptuous_serialize

from menuai.components import automation, zone
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.device_tracker import DOMAIN, device_trigger
from menuai.const import EntityCategory
from menuai.core import menuai, ServiceCall
from menuai.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from menuai.helpers.entity_registry import RegistryEntryHider
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_get_device_automations


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


AWAY_LATITUDE = 32.881011
AWAY_LONGITUDE = -117.234758

HOME_LATITUDE = 32.880837
HOME_LONGITUDE = -117.237561


@pytest.fixture(autouse=True)
async def setup_zone(menuai: menuai) -> None:
    """Create test zone."""
    await async_setup_component(
        menuai,
        zone.DOMAIN,
        {
            "zone": {
                "name": "test",
                "latitude": HOME_LATITUDE,
                "longitude": HOME_LONGITUDE,
                "radius": 250,
            }
        },
    )


async def test_get_triggers(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected triggers from a device_tracker."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": False},
        }
        for trigger in ("leaves", "enters")
    ]
    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert triggers == unordered(expected_triggers)


@pytest.mark.parametrize(
    ("hidden_by", "entity_category"),
    [
        (RegistryEntryHider.INTEGRATION, None),
        (RegistryEntryHider.USER, None),
        (None, EntityCategory.CONFIG),
        (None, EntityCategory.DIAGNOSTIC),
    ],
)
async def test_get_triggers_hidden_auxiliary(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    hidden_by,
    entity_category,
) -> None:
    """Test we get the expected triggers from a hidden or auxiliary entity."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN,
        "test",
        "5678",
        device_id=device_entry.id,
        entity_category=entity_category,
        hidden_by=hidden_by,
    )
    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": trigger,
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
            "metadata": {"secondary": True},
        }
        for trigger in ("leaves", "enters")
    ]
    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert triggers == unordered(expected_triggers)


async def test_if_fires_on_zone_change(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for enter and leave triggers firing."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    menuai.states.async_set(
        entry.entity_id,
        "state",
        {"latitude": AWAY_LATITUDE, "longitude": AWAY_LONGITUDE},
    )

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "enters",
                        "zone": "zone.test",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "enter "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ "
                                "    trigger.from_state.attributes.longitude|round(3) "
                                "  }} "
                                "- {{ trigger.to_state.attributes.longitude|round(3) }}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.id,
                        "type": "leaves",
                        "zone": "zone.test",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "leave "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ "
                                "    trigger.from_state.attributes.longitude|round(3) "
                                "  }} "
                                "- {{ trigger.to_state.attributes.longitude|round(3)}}"
                            )
                        },
                    },
                },
            ]
        },
    )

    # Fake that the entity is entering.
    menuai.states.async_set(
        entry.entity_id,
        "state",
        {"latitude": HOME_LATITUDE, "longitude": HOME_LONGITUDE},
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == f"enter - device - {entry.entity_id} - -117.235 - -117.238"
    )

    # Fake that the entity is leaving.
    menuai.states.async_set(
        entry.entity_id,
        "state",
        {"latitude": AWAY_LATITUDE, "longitude": AWAY_LONGITUDE},
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert (
        service_calls[1].data["some"]
        == f"leave - device - {entry.entity_id} - -117.238 - -117.235"
    )


async def test_if_fires_on_zone_change_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    service_calls: list[ServiceCall],
) -> None:
    """Test for enter and leave triggers firing."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )

    menuai.states.async_set(
        entry.entity_id,
        "state",
        {"latitude": AWAY_LATITUDE, "longitude": AWAY_LONGITUDE},
    )

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": device_entry.id,
                        "entity_id": entry.entity_id,
                        "type": "enters",
                        "zone": "zone.test",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "enter "
                                "- {{ trigger.platform }} "
                                "- {{ trigger.entity_id }} "
                                "- {{ "
                                "    trigger.from_state.attributes.longitude|round(3) "
                                "  }} "
                                "- {{ trigger.to_state.attributes.longitude|round(3) }}"
                            )
                        },
                    },
                },
            ]
        },
    )

    # Fake that the entity is entering.
    menuai.states.async_set(
        entry.entity_id,
        "state",
        {"latitude": HOME_LATITUDE, "longitude": HOME_LONGITUDE},
    )
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == f"enter - device - {entry.entity_id} - -117.235 - -117.238"
    )


async def test_get_trigger_capabilities(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected capabilities from a device_tracker trigger."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    capabilities = await device_trigger.async_get_trigger_capabilities(
        menuai,
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": "enters",
            "device_id": device_entry.id,
            "entity_id": entity_entry.id,
        },
    )
    assert capabilities and "extra_fields" in capabilities

    assert voluptuous_serialize.convert(
        capabilities["extra_fields"], custom_serializer=cv.custom_serializer
    ) == [
        {
            "name": "zone",
            "required": True,
            "type": "select",
            "options": [("zone.test", "test"), ("zone.home", "test home")],
        }
    ]


async def test_get_trigger_capabilities_legacy(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected capabilities from a device_tracker trigger."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_entry = entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    capabilities = await device_trigger.async_get_trigger_capabilities(
        menuai,
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": "enters",
            "device_id": device_entry.id,
            "entity_id": entity_entry.entity_id,
        },
    )
    assert capabilities and "extra_fields" in capabilities

    assert voluptuous_serialize.convert(
        capabilities["extra_fields"], custom_serializer=cv.custom_serializer
    ) == [
        {
            "name": "zone",
            "required": True,
            "type": "select",
            "options": [("zone.test", "test"), ("zone.home", "test home")],
        }
    ]
