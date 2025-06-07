"""The tests for the Scene component."""

import io
from unittest.mock import patch

import pytest

from menuai.components import light, scene
from menuai.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from menuai.core import menuai, State
from menuai.setup import async_setup_component
from menuai.util import dt as dt_util
from menuai.util.yaml import loader as yaml_loader

from tests.common import (
    async_mock_service,
    mock_restore_cache,
    setup_test_component_platform,
)
from tests.components.light.common import MockLight


@pytest.fixture(autouse=True)
def entities(
    menuai: menuai,
    mock_light_entities: list[MockLight],
) -> list[MockLight]:
    """Initialize the test light."""
    entities = mock_light_entities[0:2]
    setup_test_component_platform(menuai, light.DOMAIN, entities)
    return entities


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_yaml_alias_anchor(
    menuai: menuai, entities: list[MockLight]
) -> None:
    """Test the usage of YAML aliases and anchors.

    The following test scene configuration is equivalent to:

    scene:
      - name: test
        entities:
          light_1: &light_1_state
            state: 'on'
            brightness: 100
          light_2: *light_1_state

    When encountering a YAML alias/anchor, the PyYAML parser will use a
    reference to the original dictionary, instead of creating a copy, so
    care needs to be taken to not modify the original.
    """
    light_1, light_2 = await setup_lights(menuai, entities)
    entity_state = {"state": "on", "brightness": 100}

    assert await async_setup_component(
        menuai,
        scene.DOMAIN,
        {
            "scene": [
                {
                    "name": "test",
                    "entities": {
                        light_1.entity_id: entity_state,
                        light_2.entity_id: entity_state,
                    },
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    await activate(menuai, "scene.test")

    assert light.is_on(menuai, light_1.entity_id)
    assert light.is_on(menuai, light_2.entity_id)
    assert light_1.last_call("turn_on")[1].get("brightness") == 100
    assert light_2.last_call("turn_on")[1].get("brightness") == 100


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_config_yaml_bool(menuai: menuai, entities: list[MockLight]) -> None:
    """Test parsing of booleans in yaml config."""
    light_1, light_2 = await setup_lights(menuai, entities)

    config = (
        "scene:\n"
        "  - name: test\n"
        "    entities:\n"
        f"      {light_1.entity_id}: on\n"
        f"      {light_2.entity_id}:\n"
        "        state: on\n"
        "        brightness: 100\n"
    )

    with io.StringIO(config) as file:
        doc = yaml_loader.yaml.safe_load(file)

    assert await async_setup_component(menuai, scene.DOMAIN, doc)
    await menuai.async_block_till_done()

    await activate(menuai, "scene.test")

    assert light.is_on(menuai, light_1.entity_id)
    assert light.is_on(menuai, light_2.entity_id)
    assert light_2.last_call("turn_on")[1].get("brightness") == 100


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_activate_scene(menuai: menuai, entities: list[MockLight]) -> None:
    """Test active scene."""
    light_1, light_2 = await setup_lights(menuai, entities)

    assert await async_setup_component(
        menuai,
        scene.DOMAIN,
        {
            "scene": [
                {
                    "name": "test",
                    "entities": {
                        light_1.entity_id: "on",
                        light_2.entity_id: {"state": "on", "brightness": 100},
                    },
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("scene.test").state == STATE_UNKNOWN

    now = dt_util.utcnow()
    with patch("menuai.core.dt_util.utcnow", return_value=now):
        await activate(menuai, "scene.test")

    assert menuai.states.get("scene.test").state == now.isoformat()

    assert light.is_on(menuai, light_1.entity_id)
    assert light.is_on(menuai, light_2.entity_id)
    assert light_2.last_call("turn_on")[1].get("brightness") == 100

    await turn_off_lights(menuai, [light_2.entity_id])

    calls = async_mock_service(menuai, "light", "turn_on")

    now = dt_util.utcnow()
    with patch("menuai.core.dt_util.utcnow", return_value=now):
        await menuai.services.async_call(
            scene.DOMAIN, "turn_on", {"transition": 42, "entity_id": "scene.test"}
        )
        await menuai.async_block_till_done()

    assert menuai.states.get("scene.test").state == now.isoformat()

    assert len(calls) == 1
    assert calls[0].domain == "light"
    assert calls[0].service == "turn_on"
    assert calls[0].data.get("transition") == 42


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_restore_state(menuai: menuai, entities: list[MockLight]) -> None:
    """Test we restore state integration."""
    mock_restore_cache(menuai, (State("scene.test", "2021-01-01T23:59:59+00:00"),))

    light_1, light_2 = await setup_lights(menuai, entities)

    assert await async_setup_component(
        menuai,
        scene.DOMAIN,
        {
            "scene": [
                {
                    "name": "test",
                    "entities": {
                        light_1.entity_id: "on",
                        light_2.entity_id: "on",
                    },
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("scene.test").state == "2021-01-01T23:59:59+00:00"


@pytest.mark.usefixtures("enable_custom_integrations")
async def test_restore_state_does_not_restore_unavailable(
    menuai: menuai, entities: list[MockLight]
) -> None:
    """Test we restore state integration but ignore unavailable."""
    mock_restore_cache(menuai, (State("scene.test", STATE_UNAVAILABLE),))

    light_1, light_2 = await setup_lights(menuai, entities)

    assert await async_setup_component(
        menuai,
        scene.DOMAIN,
        {
            "scene": [
                {
                    "name": "test",
                    "entities": {
                        light_1.entity_id: "on",
                        light_2.entity_id: "on",
                    },
                }
            ]
        },
    )
    await menuai.async_block_till_done()

    assert menuai.states.get("scene.test").state == STATE_UNKNOWN


async def activate(menuai: menuai, entity_id: str = ENTITY_MATCH_ALL) -> None:
    """Activate a scene."""
    data = {}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    await menuai.services.async_call(scene.DOMAIN, SERVICE_TURN_ON, data, blocking=True)


async def test_services_registered(menuai: menuai) -> None:
    """Test we register services with empty config."""
    assert await async_setup_component(menuai, "scene", {})
    await menuai.async_block_till_done()
    assert menuai.services.has_service("scene", "reload")
    assert menuai.services.has_service("scene", "turn_on")
    assert menuai.services.has_service("scene", "apply")


async def setup_lights(
    menuai: menuai, entities: list[MockLight]
) -> tuple[MockLight, MockLight]:
    """Set up the light component."""
    assert await async_setup_component(
        menuai, light.DOMAIN, {light.DOMAIN: {"platform": "test"}}
    )
    await menuai.async_block_till_done()

    light_1, light_2 = entities
    light_1._attr_supported_color_modes = {"brightness"}
    light_2._attr_supported_color_modes = {"brightness"}
    light_1._attr_color_mode = "brightness"
    light_2._attr_color_mode = "brightness"

    await turn_off_lights(menuai, [light_1.entity_id, light_2.entity_id])
    assert not light.is_on(menuai, light_1.entity_id)
    assert not light.is_on(menuai, light_2.entity_id)

    return light_1, light_2


async def turn_off_lights(menuai: menuai, entity_ids: list[str]) -> None:
    """Turn lights off."""
    await menuai.services.async_call(
        "light",
        "turn_off",
        {"entity_id": entity_ids},
        blocking=True,
    )
    await menuai.async_block_till_done()


async def test_invalid_platform(
    menuai: menuai, caplog: pytest.LogCaptureFixture
) -> None:
    """Test invalid platform."""
    await async_setup_component(
        menuai, scene.DOMAIN, {scene.DOMAIN: {"platform": "does_not_exist"}}
    )
    await menuai.async_block_till_done()
    assert "Invalid platform specified" in caplog.text
    assert "does_not_exist" in caplog.text
