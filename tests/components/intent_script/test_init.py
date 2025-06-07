"""Test intent_script component."""

from unittest.mock import patch

from menuai import config as menuai_config
from menuai.components.intent_script import DOMAIN
from menuai.const import ATTR_FRIENDLY_NAME, SERVICE_RELOAD
from menuai.core import menuai
from menuai.helpers import (
    area_registry as ar,
    entity_registry as er,
    floor_registry as fr,
    intent,
)
from menuai.setup import async_setup_component

from tests.common import async_mock_service, get_fixture_path


async def test_intent_script(menuai: menuai) -> None:
    """Test intent scripts work."""
    calls = async_mock_service(menuai, "test", "service")

    await async_setup_component(
        menuai,
        "intent_script",
        {
            "intent_script": {
                "HelloWorld": {
                    "description": "Intent to control a test service.",
                    "platforms": ["switch"],
                    "action": {
                        "service": "test.service",
                        "data_template": {"hello": "{{ name }}"},
                    },
                    "card": {
                        "title": "Hello {{ name }}",
                        "content": "Content for {{ name }}",
                    },
                    "speech": {"text": "Good morning {{ name }}"},
                }
            }
        },
    )

    handlers = [
        intent_handler
        for intent_handler in intent.async_get(menuai)
        if intent_handler.intent_type == "HelloWorld"
    ]

    assert len(handlers) == 1
    handler = handlers[0]
    assert handler.description == "Intent to control a test service."
    assert handler.platforms == {"switch"}

    response = await intent.async_handle(
        menuai, "test", "HelloWorld", {"name": {"value": "Paulus"}}
    )

    assert len(calls) == 1
    assert calls[0].data["hello"] == "Paulus"

    assert response.speech["plain"]["speech"] == "Good morning Paulus"

    assert not (response.reprompt)

    assert response.card["simple"]["title"] == "Hello Paulus"
    assert response.card["simple"]["content"] == "Content for Paulus"


async def test_intent_script_wait_response(menuai: menuai) -> None:
    """Test intent scripts work."""
    calls = async_mock_service(menuai, "test", "service")

    await async_setup_component(
        menuai,
        "intent_script",
        {
            "intent_script": {
                "HelloWorldWaitResponse": {
                    "action": {
                        "service": "test.service",
                        "data_template": {"hello": "{{ name }}"},
                    },
                    "card": {
                        "title": "Hello {{ name }}",
                        "content": "Content for {{ name }}",
                    },
                    "speech": {"text": "Good morning {{ name }}"},
                    "reprompt": {
                        "text": "I didn't hear you, {{ name }}... I said good morning!"
                    },
                }
            }
        },
    )

    handlers = [
        intent_handler
        for intent_handler in intent.async_get(menuai)
        if intent_handler.intent_type == "HelloWorldWaitResponse"
    ]

    assert len(handlers) == 1
    handler = handlers[0]
    assert handler.platforms is None

    response = await intent.async_handle(
        menuai, "test", "HelloWorldWaitResponse", {"name": {"value": "Paulus"}}
    )

    assert len(calls) == 1
    assert calls[0].data["hello"] == "Paulus"

    assert response.speech["plain"]["speech"] == "Good morning Paulus"

    assert (
        response.reprompt["plain"]["reprompt"]
        == "I didn't hear you, Paulus... I said good morning!"
    )

    assert response.card["simple"]["title"] == "Hello Paulus"
    assert response.card["simple"]["content"] == "Content for Paulus"


async def test_intent_script_service_response(menuai: menuai) -> None:
    """Test intent scripts work."""
    calls = async_mock_service(
        menuai, "test", "service", response={"some_key": "some value"}
    )

    await async_setup_component(
        menuai,
        "intent_script",
        {
            "intent_script": {
                "HelloWorldServiceResponse": {
                    "action": [
                        {"service": "test.service", "response_variable": "result"},
                        {"stop": "", "response_variable": "result"},
                    ],
                    "speech": {
                        "text": "The service returned {{ action_response.some_key }}"
                    },
                }
            }
        },
    )

    response = await intent.async_handle(menuai, "test", "HelloWorldServiceResponse")

    assert len(calls) == 1
    assert calls[0].return_response

    assert response.speech["plain"]["speech"] == "The service returned some value"


async def test_intent_script_falsy_reprompt(menuai: menuai) -> None:
    """Test intent scripts work."""
    calls = async_mock_service(menuai, "test", "service")

    await async_setup_component(
        menuai,
        "intent_script",
        {
            "intent_script": {
                "HelloWorld": {
                    "action": {
                        "service": "test.service",
                        "data_template": {"hello": "{{ name }}"},
                    },
                    "card": {
                        "title": "Hello {{ name }}",
                        "content": "Content for {{ name }}",
                    },
                    "speech": {
                        "type": "ssml",
                        "text": '<speak><amazon:effect name="whispered">Good morning {{ name }}</amazon:effect></speak>',
                    },
                    "reprompt": {"text": "{{ null }}"},
                }
            }
        },
    )

    response = await intent.async_handle(
        menuai, "test", "HelloWorld", {"name": {"value": "Paulus"}}
    )

    assert len(calls) == 1
    assert calls[0].data["hello"] == "Paulus"

    assert (
        response.speech["ssml"]["speech"]
        == '<speak><amazon:effect name="whispered">Good morning Paulus</amazon:effect></speak>'
    )

    assert not (response.reprompt)

    assert response.card["simple"]["title"] == "Hello Paulus"
    assert response.card["simple"]["content"] == "Content for Paulus"


async def test_intent_script_targets(
    menuai: menuai,
    area_registry: ar.AreaRegistry,
    entity_registry: er.EntityRegistry,
    floor_registry: fr.FloorRegistry,
) -> None:
    """Test intent scripts work."""
    calls = async_mock_service(menuai, "test", "service")

    await async_setup_component(
        menuai,
        "intent_script",
        {
            "intent_script": {
                "Targets": {
                    "description": "Intent to control a test service.",
                    "action": {
                        "service": "test.service",
                        "data_template": {
                            "targets": "{{ targets if targets is defined }}",
                        },
                    },
                    "speech": {
                        "text": "{{ targets.entities[0] if targets is defined }}"
                    },
                }
            }
        },
    )

    floor_1 = floor_registry.async_create("first floor")
    kitchen = area_registry.async_get_or_create("kitchen")
    area_registry.async_update(kitchen.id, floor_id=floor_1.floor_id)
    bathroom = area_registry.async_get_or_create("bathroom")
    entity_registry.async_get_or_create(
        "light", "demo", "kitchen", suggested_object_id="kitchen"
    )
    entity_registry.async_update_entity("light.kitchen", area_id=kitchen.id)
    menuai.states.async_set(
        "light.kitchen", "off", attributes={ATTR_FRIENDLY_NAME: "overhead light"}
    )
    entity_registry.async_get_or_create(
        "light", "demo", "bathroom", suggested_object_id="bathroom"
    )
    entity_registry.async_update_entity("light.bathroom", area_id=bathroom.id)
    menuai.states.async_set(
        "light.bathroom", "off", attributes={ATTR_FRIENDLY_NAME: "overhead light"}
    )

    response = await intent.async_handle(
        menuai,
        "test",
        "Targets",
        {
            "name": {"value": "overhead light"},
            "domain": {"value": "light"},
            "preferred_area_id": {"value": "kitchen"},
        },
    )
    assert len(calls) == 1
    assert calls[0].data["targets"] == {"entities": ["light.kitchen"]}
    assert response.speech["plain"]["speech"] == "light.kitchen"
    calls.clear()

    response = await intent.async_handle(
        menuai,
        "test",
        "Targets",
        {
            "area": {"value": "kitchen"},
            "floor": {"value": "first floor"},
        },
    )
    assert len(calls) == 1
    assert calls[0].data["targets"] == {
        "entities": ["light.kitchen"],
        "areas": ["kitchen"],
        "floors": ["first_floor"],
    }
    calls.clear()

    response = await intent.async_handle(
        menuai,
        "test",
        "Targets",
        {"device_class": {"value": "door"}},
    )
    assert len(calls) == 1
    assert calls[0].data["targets"] == ""
    calls.clear()


async def test_reload(menuai: menuai) -> None:
    """Verify we can reload intent config."""

    config = {"intent_script": {"NewIntent1": {"speech": {"text": "HelloWorld123"}}}}

    await async_setup_component(menuai, "intent_script", config)
    await menuai.async_block_till_done()

    intents = menuai.data.get(intent.DATA_KEY)

    assert len(intents) == 1
    assert intents.get("NewIntent1")

    yaml_path = get_fixture_path("configuration.yaml", "intent_script")

    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    assert len(intents) == 1

    assert intents.get("NewIntent1") is None
    assert intents.get("NewIntent2")

    yaml_path = get_fixture_path("configuration_no_entry.yaml", "intent_script")

    with patch.object(menuai_config, "YAML_CONFIG_FILE", yaml_path):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            {},
            blocking=True,
        )
        await menuai.async_block_till_done()

    # absence of intent_script from the configuration.yaml should delete all intents.
    assert len(intents) == 0
    assert intents.get("NewIntent1") is None
    assert intents.get("NewIntent2") is None
