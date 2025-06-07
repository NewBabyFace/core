"""Test Automation config panel."""

from http import HTTPStatus
import json
from typing import Any
from unittest.mock import ANY, patch

import pytest

from menuai.components import config
from menuai.components.config import scene
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.typing import ClientSessionGenerator


@pytest.fixture
async def setup_scene(menuai: menuai, scene_config: dict[str, Any]) -> None:
    """Set up scene integration."""
    assert await async_setup_component(menuai, "scene", {"scene": scene_config})
    await menuai.async_block_till_done()


@pytest.mark.parametrize("scene_config", [{}])
@pytest.mark.usefixtures("setup_scene")
async def test_create_scene(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test creating a scene."""
    with patch.object(config, "SECTIONS", [scene]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("scene")) == []

    client = await menuai_client()

    orig_data = {}
    menuai_config_store["scenes.yaml"] = orig_data

    resp = await client.post(
        "/api/config/scene/config/light_off",
        data=json.dumps(
            {
                # "id": "light_off",  # The id should be added when writing
                "name": "Lights off",
                "entities": {"light.bedroom": {"state": "off"}},
            }
        ),
    )
    await menuai.async_block_till_done()

    assert sorted(menuai.states.async_entity_ids("scene")) == [
        "scene.lights_off",
    ]

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result == {"result": "ok"}

    assert menuai_config_store["scenes.yaml"] == [
        {
            "id": "light_off",
            "name": "Lights off",
            "entities": {"light.bedroom": {"state": "off"}},
        }
    ]


@pytest.mark.parametrize("scene_config", [{}])
@pytest.mark.usefixtures("setup_scene")
async def test_update_scene(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test updating a scene."""
    with patch.object(config, "SECTIONS", [scene]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("scene")) == []

    client = await menuai_client()

    orig_data = [{"id": "light_on"}, {"id": "light_off"}]
    menuai_config_store["scenes.yaml"] = orig_data

    resp = await client.post(
        "/api/config/scene/config/light_off",
        data=json.dumps(
            {
                "id": "light_off",
                "name": "Lights off",
                "entities": {"light.bedroom": {"state": "off"}},
            }
        ),
    )
    await menuai.async_block_till_done()

    assert sorted(menuai.states.async_entity_ids("scene")) == [
        "scene.lights_off",
    ]

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result == {"result": "ok"}

    assert menuai_config_store["scenes.yaml"] == [
        {"id": "light_on"},
        {
            "id": "light_off",
            "name": "Lights off",
            "entities": {"light.bedroom": {"state": "off"}},
        },
    ]


@pytest.mark.parametrize("scene_config", [{}])
@pytest.mark.usefixtures("setup_scene")
async def test_bad_formatted_scene(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test that we handle scene without ID."""
    with patch.object(config, "SECTIONS", [scene]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("scene")) == []

    client = await menuai_client()

    orig_data = [
        {
            # No ID
            "entities": {"light.bedroom": "on"}
        },
        {"id": "light_off"},
    ]
    menuai_config_store["scenes.yaml"] = orig_data

    resp = await client.post(
        "/api/config/scene/config/light_off",
        data=json.dumps(
            {
                "id": "light_off",
                "name": "Lights off",
                "entities": {"light.bedroom": {"state": "off"}},
            }
        ),
    )
    await menuai.async_block_till_done()

    assert sorted(menuai.states.async_entity_ids("scene")) == [
        "scene.lights_off",
    ]

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result == {"result": "ok"}

    # Verify ID added to orig_data
    assert menuai_config_store["scenes.yaml"] == [
        {
            "id": ANY,
            "entities": {"light.bedroom": "on"},
        },
        {
            "id": "light_off",
            "name": "Lights off",
            "entities": {"light.bedroom": {"state": "off"}},
        },
    ]


@pytest.mark.parametrize(
    "scene_config",
    [
        [
            {"id": "light_on", "name": "Light on", "entities": {}},
            {"id": "light_off", "name": "Light off", "entities": {}},
        ],
    ],
)
@pytest.mark.usefixtures("setup_scene")
async def test_delete_scene(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    entity_registry: er.EntityRegistry,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test deleting a scene."""

    assert len(entity_registry.entities) == 2

    with patch.object(config, "SECTIONS", [scene]):
        assert await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("scene")) == [
        "scene.light_off",
        "scene.light_on",
    ]

    client = await menuai_client()

    orig_data = [{"id": "light_on"}, {"id": "light_off"}]
    menuai_config_store["scenes.yaml"] = orig_data

    resp = await client.delete("/api/config/scene/config/light_on")
    await menuai.async_block_till_done()

    assert sorted(menuai.states.async_entity_ids("scene")) == [
        "scene.light_off",
    ]

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result == {"result": "ok"}

    assert menuai_config_store["scenes.yaml"] == [
        {"id": "light_off"},
    ]

    assert len(entity_registry.entities) == 1


@pytest.mark.parametrize("scene_config", [{}])
@pytest.mark.usefixtures("setup_scene")
async def test_api_calls_require_admin(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_read_only_access_token: str,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test scene APIs endpoints do not work as a normal user."""
    with patch.object(config, "SECTIONS", [scene]):
        await async_setup_component(menuai, "config", {})

    menuai_config_store["scenes.yaml"] = [
        {
            "id": "light_off",
            "name": "Lights off",
            "entities": {"light.bedroom": {"state": "off"}},
        }
    ]

    client = await menuai_client(menuai_read_only_access_token)

    # Get
    resp = await client.get("/api/config/scene/config/light_off")
    assert resp.status == HTTPStatus.UNAUTHORIZED

    # Update
    resp = await client.post(
        "/api/config/scene/config/light_off",
        data=json.dumps(
            {
                "id": "light_off",
                "name": "Lights off",
                "entities": {"light.bedroom": {"state": "off"}},
            }
        ),
    )
    assert resp.status == HTTPStatus.UNAUTHORIZED

    # Delete
    resp = await client.delete("/api/config/scene/config/light_on")
    assert resp.status == HTTPStatus.UNAUTHORIZED
