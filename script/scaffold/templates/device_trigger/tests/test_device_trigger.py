"""The tests for NEW_NAME device triggers."""

from pytest_unordered import unordered

from menuai.components import automation
from menuai.components.device_automation import DeviceAutomationType
from menuai.components.NEW_DOMAIN import DOMAIN
from menuai.const import STATE_OFF, STATE_ON
from menuai.core import menuai, ServiceCall
from menuai.helpers import device_registry as dr, entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockConfigEntry, async_get_device_automations


async def test_get_triggers(
    menuai: menuai,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test we get the expected triggers from a NEW_DOMAIN."""
    config_entry = MockConfigEntry(domain="test", data={})
    config_entry.add_to_menuai(menuai)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "12:34:56:AB:CD:EF")},
    )
    entity_registry.async_get_or_create(
        DOMAIN, "test", "5678", device_id=device_entry.id
    )
    expected_triggers = [
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": "turned_off",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
        {
            "platform": "device",
            "domain": DOMAIN,
            "type": "turned_on",
            "device_id": device_entry.id,
            "entity_id": f"{DOMAIN}.test_5678",
        },
    ]
    triggers = await async_get_device_automations(
        menuai, DeviceAutomationType.TRIGGER, device_entry.id
    )
    assert triggers == unordered(expected_triggers)


async def test_if_fires_on_state_change(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test for turn_on and turn_off triggers firing."""
    menuai.states.async_set("NEW_DOMAIN.entity", STATE_OFF)

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "NEW_DOMAIN.entity",
                        "type": "turned_on",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "turn_on - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }} - "
                                "{{ trigger.id}}"
                            )
                        },
                    },
                },
                {
                    "trigger": {
                        "platform": "device",
                        "domain": DOMAIN,
                        "device_id": "",
                        "entity_id": "NEW_DOMAIN.entity",
                        "type": "turned_off",
                    },
                    "action": {
                        "service": "test.automation",
                        "data_template": {
                            "some": (
                                "turn_off - {{ trigger.platform}} - "
                                "{{ trigger.entity_id}} - {{ trigger.from_state.state}} - "
                                "{{ trigger.to_state.state}} - {{ trigger.for }} - "
                                "{{ trigger.id}}"
                            )
                        },
                    },
                },
            ]
        },
    )

    # Fake that the entity is turning on.
    menuai.states.async_set("NEW_DOMAIN.entity", STATE_ON)
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == "turn_on - device - NEW_DOMAIN.entity - off - on - None - 0"
    )

    # Fake that the entity is turning off.
    menuai.states.async_set("NEW_DOMAIN.entity", STATE_OFF)
    await menuai.async_block_till_done()
    assert len(service_calls) == 2
    assert (
        service_calls[1].data["some"]
        == "turn_off - device - NEW_DOMAIN.entity - on - off - None - 0"
    )
