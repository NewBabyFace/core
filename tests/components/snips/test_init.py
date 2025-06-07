"""Test the Snips component."""

import json
import logging

import pytest
import voluptuous as vol

from menuai.components import snips
from menuai.core import DOMAIN as menuai_DOMAIN, menuai
from menuai.helpers import issue_registry as ir
from menuai.helpers.intent import ServiceIntentHandler, async_register
from menuai.setup import async_setup_component

from tests.common import async_fire_mqtt_message, async_mock_intent, async_mock_service
from tests.typing import MqttMockHAClient


async def test_snips_config(
    menuai: menuai,
    mqtt_mock: MqttMockHAClient,
    issue_registry: ir.IssueRegistry,
) -> None:
    """Test Snips Config."""
    assert await async_setup_component(
        menuai,
        "snips",
        {
            "snips": {
                "feedback_sounds": True,
                "probability_threshold": 0.5,
                "site_ids": ["default", "remote"],
            }
        },
    )
    assert (
        menuai_DOMAIN,
        f"deprecated_system_packages_yaml_integration_{snips.DOMAIN}",
    ) in issue_registry.issues


async def test_snips_no_mqtt(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test Snips Config."""
    result = await async_setup_component(
        menuai,
        "snips",
        {
            "snips": {
                "feedback_sounds": True,
                "probability_threshold": 0.5,
                "site_ids": ["default", "remote"],
            }
        },
    )
    assert not result
    assert "MQTT integration is not available" in caplog.text


async def test_snips_bad_config(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test Snips bad config."""
    result = await async_setup_component(
        menuai,
        "snips",
        {
            "snips": {
                "feedback_sounds": "on",
                "probability": "none",
                "site_ids": "default",
            }
        },
    )
    assert not result


async def test_snips_config_feedback_on(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test Snips Config."""
    result = await async_setup_component(
        menuai, "snips", {"snips": {"feedback_sounds": True}}
    )
    assert result
    await menuai.async_block_till_done()

    assert mqtt_mock.async_publish.call_count == 2
    topic = mqtt_mock.async_publish.call_args_list[0][0][0]
    assert topic == "hermes/feedback/sound/toggleOn"
    topic = mqtt_mock.async_publish.call_args_list[1][0][0]
    assert topic == "hermes/feedback/sound/toggleOn"
    assert mqtt_mock.async_publish.call_args_list[1][0][2] == 1
    assert mqtt_mock.async_publish.call_args_list[1][0][3]


async def test_snips_config_feedback_off(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test Snips Config."""
    result = await async_setup_component(
        menuai, "snips", {"snips": {"feedback_sounds": False}}
    )
    assert result
    await menuai.async_block_till_done()

    assert mqtt_mock.async_publish.call_count == 2
    topic = mqtt_mock.async_publish.call_args_list[0][0][0]
    assert topic == "hermes/feedback/sound/toggleOn"
    topic = mqtt_mock.async_publish.call_args_list[1][0][0]
    assert topic == "hermes/feedback/sound/toggleOff"
    assert mqtt_mock.async_publish.call_args_list[1][0][2] == 0
    assert not mqtt_mock.async_publish.call_args_list[1][0][3]


async def test_snips_config_no_feedback(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test Snips Config."""
    calls = async_mock_service(menuai, "snips", "say")
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    await menuai.async_block_till_done()
    assert len(calls) == 0


async def test_snips_intent(menuai: menuai, mqtt_mock: MqttMockHAClient) -> None:
    """Test intent via Snips."""
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    payload = """
    {
        "siteId": "default",
        "sessionId": "1234567890ABCDEF",
        "input": "turn the lights green",
        "intent": {
            "intentName": "Lights",
            "confidenceScore": 1
        },
        "slots": [
            {
                "slotName": "light_color",
                "value": {
                    "kind": "Custom",
                    "value": "green"
                },
                "rawValue": "green"
            }
        ]
    }
    """

    intents = async_mock_intent(menuai, "Lights")

    async_fire_mqtt_message(menuai, "hermes/intent/Lights", payload)
    await menuai.async_block_till_done()
    assert len(intents) == 1
    intent = intents[0]
    assert intent.platform == "snips"
    assert intent.intent_type == "Lights"
    assert intent
    assert intent.slots == {
        "light_color": {"value": "green"},
        "light_color_raw": {"value": "green"},
        "confidenceScore": {"value": 1},
        "site_id": {"value": "default"},
        "session_id": {"value": "1234567890ABCDEF"},
    }
    assert intent.text_input == "turn the lights green"


async def test_snips_service_intent(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test ServiceIntentHandler via Snips."""
    menuai.states.async_set("light.kitchen", "off")
    calls = async_mock_service(menuai, "light", "turn_on")
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    payload = """
    {
        "input": "turn the light on",
        "intent": {
            "intentName": "Lights",
            "confidenceScore": 0.85
        },
        "siteId": "default",
        "slots": [
            {
                "slotName": "name",
                "value": {
                    "kind": "Custom",
                    "value": "kitchen"
                },
                "rawValue": "green"
            }
        ]
    }
    """

    async_register(
        menuai, ServiceIntentHandler("Lights", "light", "turn_on", "Turned {} on")
    )

    async_fire_mqtt_message(menuai, "hermes/intent/Lights", payload)
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].domain == "light"
    assert calls[0].service == "turn_on"
    assert calls[0].data["entity_id"] == "light.kitchen"
    assert "confidenceScore" not in calls[0].data
    assert "site_id" not in calls[0].data


async def test_snips_intent_with_duration(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test intent with Snips duration."""
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    payload = """
    {
      "input": "set a timer of five minutes",
      "intent": {
        "intentName": "SetTimer",
        "confidenceScore": 1
      },
      "slots": [
        {
          "rawValue": "five minutes",
          "value": {
            "kind": "Duration",
            "years": 0,
            "quarters": 0,
            "months": 0,
            "weeks": 0,
            "days": 0,
            "hours": 0,
            "minutes": 5,
            "seconds": 0,
            "precision": "Exact"
          },
          "range": {
            "start": 15,
            "end": 27
          },
          "entity": "snips/duration",
          "slotName": "timer_duration"
        }
      ]
    }
    """
    intents = async_mock_intent(menuai, "SetTimer")

    async_fire_mqtt_message(menuai, "hermes/intent/SetTimer", payload)
    await menuai.async_block_till_done()
    assert len(intents) == 1
    intent = intents[0]
    assert intent.platform == "snips"
    assert intent.intent_type == "SetTimer"
    assert intent.slots == {
        "confidenceScore": {"value": 1},
        "site_id": {"value": None},
        "session_id": {"value": None},
        "timer_duration": {"value": 300},
        "timer_duration_raw": {"value": "five minutes"},
    }


async def test_intent_speech_response(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test intent speech response via Snips."""
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    result = await async_setup_component(
        menuai,
        "intent_script",
        {
            "intent_script": {
                "spokenIntent": {
                    "speech": {"type": "plain", "text": "I am speaking to you"}
                }
            }
        },
    )
    assert result
    payload = """
    {
        "input": "speak to me",
        "sessionId": "abcdef0123456789",
        "intent": {
            "intentName": "spokenIntent",
            "confidenceScore": 1
        },
        "slots": []
    }
    """
    async_fire_mqtt_message(menuai, "hermes/intent/spokenIntent", payload)
    await menuai.async_block_till_done()

    assert mqtt_mock.async_publish.call_count == 1
    payload = json.loads(mqtt_mock.async_publish.call_args[0][1])
    topic = mqtt_mock.async_publish.call_args[0][0]
    assert payload["sessionId"] == "abcdef0123456789"
    assert payload["text"] == "I am speaking to you"
    assert topic == "hermes/dialogueManager/endSession"


async def test_unknown_intent(
    menuai: menuai, caplog: pytest.LogCaptureFixture, mqtt_mock: MqttMockHAClient
) -> None:
    """Test unknown intent."""
    caplog.set_level(logging.WARNING)
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    payload = """
    {
        "input": "I don't know what I am supposed to do",
        "sessionId": "abcdef1234567890",
        "intent": {
            "intentName": "unknownIntent",
            "confidenceScore": 1
        },
        "slots": []
    }
    """
    async_fire_mqtt_message(menuai, "hermes/intent/unknownIntent", payload)
    await menuai.async_block_till_done()
    assert "Received unknown intent unknownIntent" in caplog.text


async def test_snips_intent_user(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test intentName format user_XXX__intentName."""
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    payload = """
    {
        "input": "what to do",
        "intent": {
            "intentName": "user_ABCDEF123__Lights",
            "confidenceScore": 1
        },
        "slots": []
    }
    """
    intents = async_mock_intent(menuai, "Lights")
    async_fire_mqtt_message(menuai, "hermes/intent/user_ABCDEF123__Lights", payload)
    await menuai.async_block_till_done()

    assert len(intents) == 1
    intent = intents[0]
    assert intent.platform == "snips"
    assert intent.intent_type == "Lights"


async def test_snips_intent_username(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test intentName format username:intentName."""
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    payload = """
    {
        "input": "what to do",
        "intent": {
            "intentName": "username:Lights",
            "confidenceScore": 1
        },
        "slots": []
    }
    """
    intents = async_mock_intent(menuai, "Lights")
    async_fire_mqtt_message(menuai, "hermes/intent/username:Lights", payload)
    await menuai.async_block_till_done()

    assert len(intents) == 1
    intent = intents[0]
    assert intent.platform == "snips"
    assert intent.intent_type == "Lights"


async def test_snips_low_probability(
    menuai: menuai, caplog: pytest.LogCaptureFixture, mqtt_mock: MqttMockHAClient
) -> None:
    """Test intent via Snips."""
    caplog.set_level(logging.WARNING)
    result = await async_setup_component(
        menuai, "snips", {"snips": {"probability_threshold": 0.5}}
    )
    assert result
    payload = """
    {
        "input": "I am not sure what to say",
        "intent": {
            "intentName": "LightsMaybe",
            "confidenceScore": 0.49
        },
        "slots": []
    }
    """

    async_mock_intent(menuai, "LightsMaybe")
    async_fire_mqtt_message(menuai, "hermes/intent/LightsMaybe", payload)
    await menuai.async_block_till_done()
    assert "Intent below probaility threshold 0.49 < 0.5" in caplog.text


async def test_intent_special_slots(
    menuai: menuai, mqtt_mock: MqttMockHAClient
) -> None:
    """Test intent special slot values via Snips."""
    calls = async_mock_service(menuai, "light", "turn_on")
    result = await async_setup_component(menuai, "snips", {"snips": {}})
    assert result
    result = await async_setup_component(
        menuai,
        "intent_script",
        {
            "intent_script": {
                "Lights": {
                    "action": {
                        "service": "light.turn_on",
                        "data_template": {
                            "confidenceScore": "{{ confidenceScore }}",
                            "site_id": "{{ site_id }}",
                        },
                    }
                }
            }
        },
    )
    assert result
    payload = """
    {
        "input": "turn the light on",
        "intent": {
            "intentName": "Lights",
            "confidenceScore": 0.85
        },
        "siteId": "default",
        "slots": []
    }
    """
    async_fire_mqtt_message(menuai, "hermes/intent/Lights", payload)
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].domain == "light"
    assert calls[0].service == "turn_on"
    assert calls[0].data["confidenceScore"] == 0.85
    assert calls[0].data["site_id"] == "default"


async def test_snips_say(menuai: menuai) -> None:
    """Test snips say with invalid config."""
    calls = async_mock_service(menuai, "snips", "say", snips.SERVICE_SCHEMA_SAY)
    data = {"text": "Hello"}
    await menuai.services.async_call("snips", "say", data)
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].domain == "snips"
    assert calls[0].service == "say"
    assert calls[0].data["text"] == "Hello"


async def test_snips_say_action(menuai: menuai) -> None:
    """Test snips say_action with invalid config."""
    calls = async_mock_service(
        menuai, "snips", "say_action", snips.SERVICE_SCHEMA_SAY_ACTION
    )

    data = {"text": "Hello", "intent_filter": ["myIntent"]}
    await menuai.services.async_call("snips", "say_action", data)
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].domain == "snips"
    assert calls[0].service == "say_action"
    assert calls[0].data["text"] == "Hello"
    assert calls[0].data["intent_filter"] == ["myIntent"]


async def test_snips_say_invalid_config(menuai: menuai) -> None:
    """Test snips say with invalid config."""
    calls = async_mock_service(menuai, "snips", "say", snips.SERVICE_SCHEMA_SAY)

    data = {"text": "Hello", "badKey": "boo"}
    with pytest.raises(vol.Invalid):
        await menuai.services.async_call("snips", "say", data)
    await menuai.async_block_till_done()

    assert len(calls) == 0


async def test_snips_say_action_invalid(menuai: menuai) -> None:
    """Test snips say_action with invalid config."""
    calls = async_mock_service(
        menuai, "snips", "say_action", snips.SERVICE_SCHEMA_SAY_ACTION
    )

    data = {"text": "Hello", "can_be_enqueued": "notabool"}

    with pytest.raises(vol.Invalid):
        await menuai.services.async_call("snips", "say_action", data)
    await menuai.async_block_till_done()

    assert len(calls) == 0


async def test_snips_feedback_on(menuai: menuai) -> None:
    """Test snips say with invalid config."""
    calls = async_mock_service(
        menuai, "snips", "feedback_on", snips.SERVICE_SCHEMA_FEEDBACK
    )

    data = {"site_id": "remote"}
    await menuai.services.async_call("snips", "feedback_on", data)
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].domain == "snips"
    assert calls[0].service == "feedback_on"
    assert calls[0].data["site_id"] == "remote"


async def test_snips_feedback_off(menuai: menuai) -> None:
    """Test snips say with invalid config."""
    calls = async_mock_service(
        menuai, "snips", "feedback_off", snips.SERVICE_SCHEMA_FEEDBACK
    )

    data = {"site_id": "remote"}
    await menuai.services.async_call("snips", "feedback_off", data)
    await menuai.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].domain == "snips"
    assert calls[0].service == "feedback_off"
    assert calls[0].data["site_id"] == "remote"


async def test_snips_feedback_config(menuai: menuai) -> None:
    """Test snips say with invalid config."""
    calls = async_mock_service(
        menuai, "snips", "feedback_on", snips.SERVICE_SCHEMA_FEEDBACK
    )

    data = {"site_id": "remote", "test": "test"}
    with pytest.raises(vol.Invalid):
        await menuai.services.async_call("snips", "feedback_on", data)
    await menuai.async_block_till_done()

    assert len(calls) == 0
