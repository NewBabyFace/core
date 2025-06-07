"""Test MenuAI scenes."""

from unittest.mock import patch

import pytest
import voluptuous as vol

from menuai.components.menuai import scene as ha_scene
from menuai.components.menuai.scene import EVENT_SCENE_RELOADED
from menuai.const import STATE_UNKNOWN
from menuai.core import menuai
from menuai.exceptions import ServiceValidationError
from menuai.setup import async_setup_component

from tests.common import async_capture_events, async_mock_service


async def test_reload_config_service(menuai: menuai) -> None:
    """Test the reload config service."""
    assert await async_setup_component(menuai, "scene", {})
    await menuai.async_block_till_done()

    test_reloaded_event = async_capture_events(menuai, EVENT_SCENE_RELOADED)

    with patch(
        "menuai.config.load_yaml_config_file",
        autospec=True,
        return_value={"scene": {"name": "Hallo", "entities": {"light.kitchen": "on"}}},
    ):
        await menuai.services.async_call("scene", "reload", blocking=True)
        await menuai.async_block_till_done()

    assert menuai.states.get("scene.hallo") is not None
    assert len(test_reloaded_event) == 1

    with patch(
        "menuai.config.load_yaml_config_file",
        autospec=True,
        return_value={"scene": {"name": "Bye", "entities": {"light.kitchen": "on"}}},
    ):
        await menuai.services.async_call("scene", "reload", blocking=True)
        await menuai.async_block_till_done()

    assert len(test_reloaded_event) == 2
    assert menuai.states.get("scene.hallo") is None
    assert menuai.states.get("scene.bye") is not None


async def test_apply_service(menuai: menuai) -> None:
    """Test the apply service."""
    assert await async_setup_component(menuai, "scene", {})
    assert await async_setup_component(menuai, "light", {"light": {"platform": "demo"}})
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        "scene", "apply", {"entities": {"light.bed_light": "off"}}, blocking=True
    )

    assert menuai.states.get("light.bed_light").state == "off"

    await menuai.services.async_call(
        "scene",
        "apply",
        {"entities": {"light.bed_light": {"state": "on", "brightness": 50}}},
        blocking=True,
    )

    state = menuai.states.get("light.bed_light")
    assert state.state == "on"
    assert state.attributes["brightness"] == 50

    turn_on_calls = async_mock_service(menuai, "light", "turn_on")
    await menuai.services.async_call(
        "scene",
        "apply",
        {
            "transition": 42,
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
        },
        blocking=True,
    )

    assert len(turn_on_calls) == 1
    assert turn_on_calls[0].domain == "light"
    assert turn_on_calls[0].service == "turn_on"
    assert turn_on_calls[0].data.get("transition") == 42
    assert turn_on_calls[0].data.get("entity_id") == "light.bed_light"
    assert turn_on_calls[0].data.get("brightness") == 50


async def test_create_service(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the create service."""
    assert await async_setup_component(
        menuai,
        "scene",
        {"scene": {"name": "hallo_2", "entities": {"light.kitchen": "on"}}},
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("scene.hallo") is None
    assert menuai.states.get("scene.hallo_2") is not None

    await menuai.services.async_call(
        "scene",
        "create",
        {"scene_id": "hallo", "entities": {}, "snapshot_entities": []},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert "Empty scenes are not allowed" in caplog.text
    assert menuai.states.get("scene.hallo") is None

    await menuai.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo",
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    scene = menuai.states.get("scene.hallo")
    assert scene is not None
    assert scene.domain == "scene"
    assert scene.name == "hallo"
    assert scene.state == STATE_UNKNOWN
    assert scene.attributes.get("entity_id") == ["light.bed_light"]

    await menuai.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo",
            "entities": {"light.kitchen_light": {"state": "on", "brightness": 100}},
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    scene = menuai.states.get("scene.hallo")
    assert scene is not None
    assert scene.domain == "scene"
    assert scene.name == "hallo"
    assert scene.state == STATE_UNKNOWN
    assert scene.attributes.get("entity_id") == ["light.kitchen_light"]

    await menuai.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo_2",
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    assert "The scene scene.hallo_2 already exists" in caplog.text
    scene = menuai.states.get("scene.hallo_2")
    assert scene is not None
    assert scene.domain == "scene"
    assert scene.name == "hallo_2"
    assert scene.state == STATE_UNKNOWN
    assert scene.attributes.get("entity_id") == ["light.kitchen"]


async def test_delete_service(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the delete service."""
    assert await async_setup_component(
        menuai,
        "scene",
        {"scene": {"name": "hallo_2", "entities": {"light.kitchen": "on"}}},
    )
    await menuai.async_block_till_done()

    await menuai.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo",
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            "scene",
            "delete",
            {
                "entity_id": "scene.hallo_3",
            },
            blocking=True,
        )

    with pytest.raises(ServiceValidationError):
        await menuai.services.async_call(
            "scene",
            "delete",
            {
                "entity_id": "scene.hallo_2",
            },
            blocking=True,
        )
    assert menuai.states.get("scene.hallo_2") is not None

    assert menuai.states.get("scene.hallo") is not None

    await menuai.services.async_call(
        "scene",
        "delete",
        {
            "entity_id": "scene.hallo",
        },
        blocking=True,
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("state.hallo") is None


async def test_snapshot_service(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test the snapshot option."""
    assert await async_setup_component(menuai, "scene", {"scene": {}})
    await menuai.async_block_till_done()
    menuai.states.async_set("light.my_light", "on", {"hs_color": (345, 75)})
    assert menuai.states.get("scene.hallo") is None

    await menuai.services.async_call(
        "scene",
        "create",
        {"scene_id": "hallo", "snapshot_entities": ["light.my_light"]},
        blocking=True,
    )
    await menuai.async_block_till_done()
    scene = menuai.states.get("scene.hallo")
    assert scene is not None
    assert scene.attributes.get("entity_id") == ["light.my_light"]

    menuai.states.async_set("light.my_light", "off", {"hs_color": (123, 45)})
    turn_on_calls = async_mock_service(menuai, "light", "turn_on")
    await menuai.services.async_call(
        "scene", "turn_on", {"entity_id": "scene.hallo"}, blocking=True
    )
    await menuai.async_block_till_done()
    assert len(turn_on_calls) == 1
    assert turn_on_calls[0].data.get("entity_id") == "light.my_light"
    assert turn_on_calls[0].data.get("hs_color") == (345, 75)

    await menuai.services.async_call(
        "scene",
        "create",
        {"scene_id": "hallo_2", "snapshot_entities": ["light.not_existent"]},
        blocking=True,
    )
    await menuai.async_block_till_done()
    assert menuai.states.get("scene.hallo_2") is None
    assert (
        "Entity light.not_existent does not exist and therefore cannot be snapshotted"
        in caplog.text
    )

    await menuai.services.async_call(
        "scene",
        "create",
        {
            "scene_id": "hallo_3",
            "entities": {"light.bed_light": {"state": "on", "brightness": 50}},
            "snapshot_entities": ["light.my_light"],
        },
        blocking=True,
    )
    await menuai.async_block_till_done()
    scene = menuai.states.get("scene.hallo_3")
    assert scene is not None
    assert "light.my_light" in scene.attributes.get("entity_id")
    assert "light.bed_light" in scene.attributes.get("entity_id")


async def test_ensure_no_intersection(menuai: menuai) -> None:
    """Test that entities and snapshot_entities do not overlap."""
    assert await async_setup_component(menuai, "scene", {"scene": {}})
    await menuai.async_block_till_done()

    with pytest.raises(vol.MultipleInvalid) as ex:
        await menuai.services.async_call(
            "scene",
            "create",
            {
                "scene_id": "hallo",
                "entities": {"light.my_light": {"state": "on", "brightness": 50}},
                "snapshot_entities": ["light.my_light"],
            },
            blocking=True,
        )
    assert "entities and snapshot_entities must not overlap" in str(ex.value)
    assert menuai.states.get("scene.hallo") is None


async def test_scenes_with_entity(menuai: menuai) -> None:
    """Test finding scenes with a specific entity."""
    assert await async_setup_component(
        menuai,
        "scene",
        {
            "scene": [
                {"name": "scene_1", "entities": {"light.kitchen": "on"}},
                {"name": "scene_2", "entities": {"light.living_room": "off"}},
                {
                    "name": "scene_3",
                    "entities": {"light.kitchen": "on", "light.living_room": "off"},
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    assert sorted(ha_scene.scenes_with_entity(menuai, "light.kitchen")) == [
        "scene.scene_1",
        "scene.scene_3",
    ]


async def test_entities_in_scene(menuai: menuai) -> None:
    """Test finding entities in a scene."""
    assert await async_setup_component(
        menuai,
        "scene",
        {
            "scene": [
                {"name": "scene_1", "entities": {"light.kitchen": "on"}},
                {"name": "scene_2", "entities": {"light.living_room": "off"}},
                {
                    "name": "scene_3",
                    "entities": {"light.kitchen": "on", "light.living_room": "off"},
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    for scene_id, entities in (
        ("scene.scene_1", ["light.kitchen"]),
        ("scene.scene_2", ["light.living_room"]),
        ("scene.scene_3", ["light.kitchen", "light.living_room"]),
    ):
        assert ha_scene.entities_in_scene(menuai, scene_id) == entities


async def test_config(menuai: menuai) -> None:
    """Test passing config in YAML."""
    assert await async_setup_component(
        menuai,
        "scene",
        {
            "scene": [
                {
                    "id": "scene_id",
                    "name": "Scene Icon",
                    "icon": "mdi:party",
                    "entities": {"light.kitchen": "on"},
                },
                {
                    "name": "Scene No Icon",
                    "entities": {"light.kitchen": {"state": "on"}},
                },
            ]
        },
    )
    await menuai.async_block_till_done()

    icon = menuai.states.get("scene.scene_icon")
    assert icon is not None
    assert icon.attributes["icon"] == "mdi:party"

    no_icon = menuai.states.get("scene.scene_no_icon")
    assert no_icon is not None
    assert "icon" not in no_icon.attributes


def test_validator() -> None:
    """Test validators."""
    parsed = ha_scene.STATES_SCHEMA({"light.Test": {"state": "on"}})
    assert len(parsed) == 1
    assert "light.test" in parsed
    assert parsed["light.test"].entity_id == "light.test"
    assert parsed["light.test"].state == "on"
