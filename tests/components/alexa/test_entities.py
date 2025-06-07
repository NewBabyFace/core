"""Test Alexa entity representation."""

from typing import Any
from unittest.mock import patch

import pytest

from menuai.components.alexa import smart_home
from menuai.const import EntityCategory, UnitOfTemperature, __version__
from menuai.core import menuai
from menuai.helpers import entity_registry as er

from .test_common import get_default_config, get_new_request


async def test_unsupported_domain(menuai: menuai) -> None:
    """Discovery ignores entities of unknown domains."""
    request = get_new_request("Alexa.Discovery", "Discover")

    menuai.states.async_set("woz.boop", "on", {"friendly_name": "Boop Woz"})

    msg = await smart_home.async_handle_message(menuai, get_default_config(menuai), request)

    assert "event" in msg
    msg = msg["event"]

    assert not msg["payload"]["endpoints"]


async def test_categorized_hidden_entities(
    menuai: menuai, entity_registry: er.EntityRegistry
) -> None:
    """Discovery ignores hidden and categorized entities."""
    request = get_new_request("Alexa.Discovery", "Discover")

    entity_entry1 = entity_registry.async_get_or_create(
        "switch",
        "test",
        "switch_config_id",
        suggested_object_id="config_switch",
        entity_category=EntityCategory.CONFIG,
    )
    entity_entry2 = entity_registry.async_get_or_create(
        "switch",
        "test",
        "switch_diagnostic_id",
        suggested_object_id="diagnostic_switch",
        entity_category=EntityCategory.DIAGNOSTIC,
    )
    entity_entry3 = entity_registry.async_get_or_create(
        "switch",
        "test",
        "switch_hidden_integration_id",
        suggested_object_id="hidden_integration_switch",
        hidden_by=er.RegistryEntryHider.INTEGRATION,
    )
    entity_entry4 = entity_registry.async_get_or_create(
        "switch",
        "test",
        "switch_hidden_user_id",
        suggested_object_id="hidden_user_switch",
        hidden_by=er.RegistryEntryHider.USER,
    )

    # These should not show up in the sync request
    menuai.states.async_set(entity_entry1.entity_id, "on")
    menuai.states.async_set(entity_entry2.entity_id, "something_else")
    menuai.states.async_set(entity_entry3.entity_id, "blah")
    menuai.states.async_set(entity_entry4.entity_id, "foo")

    msg = await smart_home.async_handle_message(menuai, get_default_config(menuai), request)

    assert "event" in msg
    msg = msg["event"]

    assert not msg["payload"]["endpoints"]


async def test_serialize_discovery(menuai: menuai) -> None:
    """Test we can serialize a discovery."""
    request = get_new_request("Alexa.Discovery", "Discover")

    menuai.states.async_set("switch.bla", "on", {"friendly_name": "Boop Woz"})

    msg = await smart_home.async_handle_message(menuai, get_default_config(menuai), request)

    assert "event" in msg
    msg = msg["event"]
    endpoint = msg["payload"]["endpoints"][0]

    assert endpoint["additionalAttributes"] == {
        "manufacturer": "MenuAI",
        "model": "switch",
        "softwareVersion": __version__,
        "customIdentifier": "mock-user-id-switch.bla",
    }


async def test_serialize_discovery_partly_fails(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we can partly serialize a discovery."""

    async def _mock_discovery() -> dict[str, Any]:
        request = get_new_request("Alexa.Discovery", "Discover")
        menuai.states.async_set("switch.bla", "on", {"friendly_name": "My Switch"})
        menuai.states.async_set("fan.bla", "on", {"friendly_name": "My Fan"})
        menuai.states.async_set(
            "humidifier.bla", "on", {"friendly_name": "My Humidifier"}
        )
        menuai.states.async_set(
            "sensor.bla",
            "20.1",
            {
                "friendly_name": "Livingroom temperature",
                "unit_of_measurement": UnitOfTemperature.CELSIUS,
                "device_class": "temperature",
            },
        )
        return await smart_home.async_handle_message(
            menuai, get_default_config(menuai), request
        )

    msg = await _mock_discovery()
    assert "event" in msg
    msg = msg["event"]
    assert len(msg["payload"]["endpoints"]) == 4
    endpoint_ids = {
        attributes["endpointId"] for attributes in msg["payload"]["endpoints"]
    }
    assert all(
        entity in endpoint_ids
        for entity in ("switch#bla", "fan#bla", "humidifier#bla", "sensor#bla")
    )

    # Simulate fetching the interfaces fails for fan entity
    with patch(
        "menuai.components.alexa.entities.FanCapabilities.interfaces",
        side_effect=TypeError(),
    ):
        msg = await _mock_discovery()
        assert "event" in msg
        msg = msg["event"]
        assert len(msg["payload"]["endpoints"]) == 3
        endpoint_ids = {
            attributes["endpointId"] for attributes in msg["payload"]["endpoints"]
        }
        assert all(
            entity in endpoint_ids
            for entity in ("switch#bla", "humidifier#bla", "sensor#bla")
        )
        assert "Unable to serialize fan.bla for discovery" in caplog.text
        caplog.clear()

    # Simulate serializing properties fails for sensor entity
    with patch(
        "menuai.components.alexa.entities.SensorCapabilities.default_display_categories",
        side_effect=ValueError(),
    ):
        msg = await _mock_discovery()
        assert "event" in msg
        msg = msg["event"]
        assert len(msg["payload"]["endpoints"]) == 3
        endpoint_ids = {
            attributes["endpointId"] for attributes in msg["payload"]["endpoints"]
        }
        assert all(
            entity in endpoint_ids
            for entity in ("switch#bla", "humidifier#bla", "fan#bla")
        )
        assert "Unable to serialize sensor.bla for discovery" in caplog.text
        caplog.clear()


async def test_serialize_discovery_recovers(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test we handle an interface raising unexpectedly during serialize discovery."""
    request = get_new_request("Alexa.Discovery", "Discover")

    menuai.states.async_set("switch.bla", "on", {"friendly_name": "Boop Woz"})

    with patch(
        "menuai.components.alexa.capabilities.AlexaPowerController.serialize_discovery",
        side_effect=TypeError,
    ):
        msg = await smart_home.async_handle_message(
            menuai, get_default_config(menuai), request
        )

    assert "event" in msg
    msg = msg["event"]

    interfaces = {
        ifc["interface"] for ifc in msg["payload"]["endpoints"][0]["capabilities"]
    }

    assert "Alexa.PowerController" not in interfaces
    assert (
        "Error serializing Alexa.PowerController discovery"
        f" for {menuai.states.get('switch.bla')}"
    ) in caplog.text
