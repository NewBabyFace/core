"""Tests for config/script."""

from http import HTTPStatus
import json
from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import config
from menuai.components.config import script
from menuai.const import STATE_OFF, STATE_UNAVAILABLE
from menuai.core import menuai
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component
from menuai.util import yaml as yaml_util

from tests.typing import ClientSessionGenerator


@pytest.fixture(autouse=True, name="stub_blueprint_populate")
def stub_blueprint_populate_autouse(stub_blueprint_populate: None) -> None:
    """Stub copying the blueprints to the config folder."""


@pytest.fixture(autouse=True)
async def setup_script(menuai: menuai, script_config: dict[str, Any]) -> None:
    """Set up script integration."""
    assert await async_setup_component(menuai, "script", {"script": script_config})


@pytest.mark.parametrize("script_config", [{}])
async def test_get_script_config(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test getting script config."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    client = await menuai_client()

    menuai_config_store["scripts.yaml"] = {
        "sun": {"alias": "Sun"},
        "moon": {"alias": "Moon"},
    }

    resp = await client.get("/api/config/script/config/moon")

    assert resp.status == HTTPStatus.OK
    result = await resp.json()

    assert result == {"alias": "Moon"}


@pytest.mark.parametrize("script_config", [{}])
async def test_update_script_config(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test updating script config."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("script")) == []

    client = await menuai_client()

    orig_data = {"sun": {"alias": "Sun"}, "moon": {"alias": "Moon"}}
    menuai_config_store["scripts.yaml"] = orig_data

    resp = await client.post(
        "/api/config/script/config/moon",
        data=json.dumps({"alias": "Moon updated", "sequence": []}),
    )
    await menuai.async_block_till_done()
    assert sorted(menuai.states.async_entity_ids("script")) == [
        "script.moon",
        "script.sun",
    ]
    assert menuai.states.get("script.moon").state == STATE_OFF
    assert menuai.states.get("script.sun").state == STATE_UNAVAILABLE

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result == {"result": "ok"}

    new_data = menuai_config_store["scripts.yaml"]
    assert list(new_data["moon"]) == ["alias", "sequence"]
    assert new_data["moon"] == {"alias": "Moon updated", "sequence": []}


@pytest.mark.parametrize("script_config", [{}])
async def test_invalid_object_id(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test creating a script with an invalid object_id."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("script")) == []

    client = await menuai_client()

    menuai_config_store["scripts.yaml"] = {}

    resp = await client.post(
        "/api/config/script/config/turn_on",
        data=json.dumps({"alias": "Turn on", "sequence": []}),
    )
    await menuai.async_block_till_done()
    assert sorted(menuai.states.async_entity_ids("script")) == []

    assert resp.status == HTTPStatus.BAD_REQUEST
    result = await resp.json()
    assert result == {
        "message": (
            "Message malformed: A script's object_id must not be one of "
            "reload, toggle, turn_off, turn_on"
        )
    }

    new_data = menuai_config_store["scripts.yaml"]
    assert new_data == {}


@pytest.mark.parametrize("script_config", [{}])
@pytest.mark.parametrize(
    ("updated_config", "validation_error"),
    [
        ({}, "required key not provided @ data['sequence']"),
        (
            {
                "sequence": {
                    "condition": "state",
                    # The UUID will fail being resolved to en entity_id
                    "entity_id": "abcdabcdabcdabcdabcdabcdabcdabcd",
                    "state": "blah",
                }
            },
            "Unknown entity registry entry abcdabcdabcdabcdabcdabcdabcdabcd",
        ),
        (
            {
                "use_blueprint": {
                    "path": "test_service.yaml",
                    "input": {},
                },
            },
            "Missing input service_to_call",
        ),
    ],
)
async def test_update_script_config_with_error(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    updated_config: Any,
    validation_error: str,
) -> None:
    """Test updating script config with errors."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("script")) == []

    client = await menuai_client()

    orig_data = {"sun": {}, "moon": {}}
    menuai_config_store["scripts.yaml"] = orig_data

    resp = await client.post(
        "/api/config/script/config/moon",
        data=json.dumps(updated_config),
    )
    await menuai.async_block_till_done()
    assert sorted(menuai.states.async_entity_ids("script")) == []

    assert resp.status != HTTPStatus.OK
    result = await resp.json()
    assert result == {"message": f"Message malformed: {validation_error}"}
    # Assert the validation error is not logged
    assert validation_error not in caplog.text


@pytest.mark.parametrize("script_config", [{}])
@pytest.mark.parametrize(
    ("updated_config", "validation_error"),
    [
        (
            {
                "use_blueprint": {
                    "path": "test_service.yaml",
                    "input": {
                        "service_to_call": "test.automation",
                    },
                },
            },
            "No substitution found for input blah",
        ),
    ],
)
async def test_update_script_config_with_blueprint_substitution_error(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    updated_config: Any,
    validation_error: str,
) -> None:
    """Test updating script config with errors."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("script")) == []

    client = await menuai_client()

    orig_data = {"sun": {}, "moon": {}}
    menuai_config_store["scripts.yaml"] = orig_data

    with patch(
        "menuai.components.blueprint.models.BlueprintInputs.async_substitute",
        side_effect=yaml_util.UndefinedSubstitution("blah"),
    ):
        resp = await client.post(
            "/api/config/script/config/moon",
            data=json.dumps(updated_config),
        )
        await menuai.async_block_till_done()
    assert sorted(menuai.states.async_entity_ids("script")) == []

    assert resp.status != HTTPStatus.OK
    result = await resp.json()
    assert result == {"message": f"Message malformed: {validation_error}"}
    # Assert the validation error is not logged
    assert validation_error not in caplog.text


@pytest.mark.parametrize("script_config", [{}])
async def test_update_remove_key_script_config(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test updating script config while removing a key."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("script")) == []

    client = await menuai_client()

    orig_data = {"sun": {"key": "value"}, "moon": {"key": "value"}}
    menuai_config_store["scripts.yaml"] = orig_data

    resp = await client.post(
        "/api/config/script/config/moon",
        data=json.dumps({"sequence": []}),
    )
    await menuai.async_block_till_done()
    assert sorted(menuai.states.async_entity_ids("script")) == [
        "script.moon",
        "script.sun",
    ]
    assert menuai.states.get("script.moon").state == STATE_OFF
    assert menuai.states.get("script.sun").state == STATE_UNAVAILABLE

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result == {"result": "ok"}

    new_data = menuai_config_store["scripts.yaml"]
    assert list(new_data["moon"]) == ["sequence"]
    assert new_data["moon"] == {"sequence": []}


@pytest.mark.parametrize(
    "script_config",
    [
        {
            "one": {"alias": "Light on", "sequence": []},
            "two": {"alias": "Light off", "sequence": []},
        },
    ],
)
async def test_delete_script(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    entity_registry: er.EntityRegistry,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test deleting a script."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    assert sorted(menuai.states.async_entity_ids("script")) == [
        "script.one",
        "script.two",
    ]

    assert len(entity_registry.entities) == 2

    client = await menuai_client()

    orig_data = {"one": {}, "two": {}}
    menuai_config_store["scripts.yaml"] = orig_data

    resp = await client.delete("/api/config/script/config/two")
    await menuai.async_block_till_done()

    assert sorted(menuai.states.async_entity_ids("script")) == [
        "script.one",
    ]

    assert resp.status == HTTPStatus.OK
    result = await resp.json()
    assert result == {"result": "ok"}

    assert menuai_config_store["scripts.yaml"] == {"one": {}}

    assert len(entity_registry.entities) == 1


@pytest.mark.parametrize("script_config", [{}])
async def test_api_calls_require_admin(
    menuai: menuai,
    menuai_client: ClientSessionGenerator,
    menuai_read_only_access_token: str,
    menuai_config_store: dict[str, Any],
) -> None:
    """Test script APIs endpoints do not work as a normal user."""
    with patch.object(config, "SECTIONS", [script]):
        await async_setup_component(menuai, "config", {})

    menuai_config_store["scripts.yaml"] = {
        "moon": {"alias": "Moon"},
    }

    client = await menuai_client(menuai_read_only_access_token)

    # Get
    resp = await client.get("/api/config/script/config/moon")
    assert resp.status == HTTPStatus.UNAUTHORIZED

    # Update
    resp = await client.post(
        "/api/config/script/config/moon",
        data=json.dumps({"sequence": []}),
    )
    assert resp.status == HTTPStatus.UNAUTHORIZED

    # Delete
    resp = await client.delete("/api/config/script/config/moon")
    assert resp.status == HTTPStatus.UNAUTHORIZED
