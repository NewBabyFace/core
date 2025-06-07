"""The tests for the MQTT automation."""

from unittest.mock import ANY

import pytest

from menuai.components import automation
from menuai.const import ATTR_ENTITY_ID, ENTITY_MATCH_ALL, SERVICE_TURN_OFF
from menuai.core import menuaiJobType, menuai, ServiceCall
from menuai.setup import async_setup_component

from tests.common import async_fire_mqtt_message, mock_component
from tests.typing import MqttMockHAClient, MqttMockHAClientGenerator


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture(autouse=True)
async def setup_comp(
    menuai: menuai, mqtt_mock_entry: MqttMockHAClientGenerator
) -> MqttMockHAClient:
    """Initialize components."""
    mock_component(menuai, "group")
    return await mqtt_mock_entry()


async def test_if_fires_on_topic_match(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test if message is fired on topic match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "mqtt", "topic": "test-topic"},
                "action": {
                    "service": "test.automation",
                    "data_template": {
                        "some": "{{ trigger.platform }} - {{ trigger.topic }} - "
                        "{{ trigger.payload }} - {{ trigger.payload_json.hello }} - "
                        "{{ trigger.id }}"
                    },
                },
            }
        },
    )

    async_fire_mqtt_message(menuai, "test-topic", '{ "hello": "world" }')
    await menuai.async_block_till_done()
    assert len(service_calls) == 1
    assert (
        service_calls[0].data["some"]
        == 'mqtt - test-topic - { "hello": "world" } - world - 0'
    )

    await menuai.services.async_call(
        automation.DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: ENTITY_MATCH_ALL},
        blocking=True,
    )
    assert len(service_calls) == 2

    async_fire_mqtt_message(menuai, "test-topic", "test_payload")
    await menuai.async_block_till_done()
    assert len(service_calls) == 2


async def test_if_fires_on_topic_and_payload_match(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test if message is fired on topic and payload match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic",
                    "payload": "hello",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    async_fire_mqtt_message(menuai, "test-topic", "hello")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_topic_and_payload_match2(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test if message is fired on topic and payload match.

    Make sure a payload which would render as a non string can still be matched.
    """
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic",
                    "payload": "0",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    async_fire_mqtt_message(menuai, "test-topic", "0")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_templated_topic_and_payload_match(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test if message is fired on templated topic and payload match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic-{{ sqrt(16)|round }}",
                    "payload": '{{ "foo"|regex_replace("foo", "bar") }}',
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    async_fire_mqtt_message(menuai, "test-topic-", "foo")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    async_fire_mqtt_message(menuai, "test-topic-4", "foo")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    async_fire_mqtt_message(menuai, "test-topic-4", "bar")
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_if_fires_on_payload_template(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test if message is fired on templated topic and payload match."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic",
                    "payload": "hello",
                    "value_template": "{{ value_json.wanted_key }}",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    async_fire_mqtt_message(menuai, "test-topic", "hello")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    async_fire_mqtt_message(menuai, "test-topic", '{"unwanted_key":"hello"}')
    await menuai.async_block_till_done()
    assert len(service_calls) == 0

    async_fire_mqtt_message(menuai, "test-topic", '{"wanted_key":"hello"}')
    await menuai.async_block_till_done()
    assert len(service_calls) == 1


async def test_non_allowed_templates(
    menuai: menuai,
    service_calls: list[ServiceCall],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test non allowed function in template."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic-{{ states() }}",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    assert (
        "Got error 'TemplateError: Use of 'states' is not supported in limited templates' when setting up triggers"
        in caplog.text
    )


async def test_if_not_fires_on_topic_but_no_payload_match(
    menuai: menuai, service_calls: list[ServiceCall]
) -> None:
    """Test if message is not fired on topic but no payload."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {
                    "platform": "mqtt",
                    "topic": "test-topic",
                    "payload": "hello",
                },
                "action": {"service": "test.automation"},
            }
        },
    )

    async_fire_mqtt_message(menuai, "test-topic", "no-hello")
    await menuai.async_block_till_done()
    assert len(service_calls) == 0


async def test_encoding_default(
    menuai: menuai, service_calls: list[ServiceCall], setup_comp
) -> None:
    """Test default encoding."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "mqtt", "topic": "test-topic"},
                "action": {"service": "test.automation"},
            }
        },
    )

    setup_comp.async_subscribe.assert_called_with(
        "test-topic", ANY, 0, "utf-8", menuaiJobType.Callback
    )


async def test_encoding_custom(
    menuai: menuai, service_calls: list[ServiceCall], setup_comp
) -> None:
    """Test default encoding."""
    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: {
                "trigger": {"platform": "mqtt", "topic": "test-topic", "encoding": ""},
                "action": {"service": "test.automation"},
            }
        },
    )

    setup_comp.async_subscribe.assert_called_with(
        "test-topic", ANY, 0, None, menuaiJobType.Callback
    )
