"""The tests for the input_boolean component."""

import logging
from typing import Any
from unittest.mock import patch

import pytest

from menuai.components.input_boolean import CONF_INITIAL, DOMAIN, is_on
from menuai.const import (
    ATTR_EDITABLE,
    ATTR_ENTITY_ID,
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    ATTR_NAME,
    SERVICE_RELOAD,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from menuai.core import Context, CoreState, menuai, State
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from tests.common import MockUser, mock_component, mock_restore_cache
from tests.typing import WebSocketGenerator

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def storage_setup(menuai: menuai, menuai_storage: dict[str, Any]):
    """Storage setup."""

    async def _storage(items=None, config=None):
        if items is None:
            menuai_storage[DOMAIN] = {
                "key": DOMAIN,
                "version": 1,
                "data": {"items": [{"id": "from_storage", "name": "from storage"}]},
            }
        else:
            menuai_storage[DOMAIN] = {
                "key": DOMAIN,
                "version": 1,
                "data": {"items": items},
            }
        if config is None:
            config = {DOMAIN: {}}
        return await async_setup_component(menuai, DOMAIN, config)

    return _storage


async def test_config(menuai: menuai) -> None:
    """Test config."""
    invalid_configs = [None, 1, {}, {"name with space": None}]

    for cfg in invalid_configs:
        assert not await async_setup_component(menuai, DOMAIN, {DOMAIN: cfg})


async def test_methods(menuai: menuai) -> None:
    """Test is_on, turn_on, turn_off methods."""
    assert await async_setup_component(menuai, DOMAIN, {DOMAIN: {"test_1": None}})
    entity_id = "input_boolean.test_1"

    assert not is_on(menuai, entity_id)

    await menuai.services.async_call(
        DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    assert is_on(menuai, entity_id)

    await menuai.services.async_call(
        DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    assert not is_on(menuai, entity_id)

    await menuai.services.async_call(
        DOMAIN, SERVICE_TOGGLE, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )

    assert is_on(menuai, entity_id)


async def test_config_options(menuai: menuai) -> None:
    """Test configuration options."""
    count_start = len(menuai.states.async_entity_ids())

    _LOGGER.debug("ENTITIES @ start: %s", menuai.states.async_entity_ids())

    assert await async_setup_component(
        menuai,
        DOMAIN,
        {
            DOMAIN: {
                "test_1": None,
                "test_2": {"name": "Hello World", "icon": "mdi:work", "initial": True},
            }
        },
    )

    _LOGGER.debug("ENTITIES: %s", menuai.states.async_entity_ids())

    assert count_start + 2 == len(menuai.states.async_entity_ids())

    state_1 = menuai.states.get("input_boolean.test_1")
    state_2 = menuai.states.get("input_boolean.test_2")

    assert state_1 is not None
    assert state_2 is not None

    assert state_1.state == STATE_OFF
    assert ATTR_ICON not in state_1.attributes
    assert ATTR_FRIENDLY_NAME not in state_1.attributes

    assert state_2.state == STATE_ON
    assert state_2.attributes.get(ATTR_FRIENDLY_NAME) == "Hello World"
    assert state_2.attributes.get(ATTR_ICON) == "mdi:work"


async def test_restore_state(menuai: menuai) -> None:
    """Ensure states are restored on startup."""
    mock_restore_cache(
        menuai,
        (
            State("input_boolean.b1", "on"),
            State("input_boolean.b2", "off"),
            State("input_boolean.b3", "on"),
        ),
    )

    menuai.set_state(CoreState.starting)
    mock_component(menuai, "recorder")

    await async_setup_component(menuai, DOMAIN, {DOMAIN: {"b1": None, "b2": None}})

    state = menuai.states.get("input_boolean.b1")
    assert state
    assert state.state == "on"

    state = menuai.states.get("input_boolean.b2")
    assert state
    assert state.state == "off"


async def test_initial_state_overrules_restore_state(menuai: menuai) -> None:
    """Ensure states are restored on startup."""
    mock_restore_cache(
        menuai, (State("input_boolean.b1", "on"), State("input_boolean.b2", "off"))
    )

    menuai.set_state(CoreState.starting)

    await async_setup_component(
        menuai,
        DOMAIN,
        {DOMAIN: {"b1": {CONF_INITIAL: False}, "b2": {CONF_INITIAL: True}}},
    )

    state = menuai.states.get("input_boolean.b1")
    assert state
    assert state.state == "off"

    state = menuai.states.get("input_boolean.b2")
    assert state
    assert state.state == "on"


async def test_input_boolean_context(
    menuai: menuai, menuai_admin_user: MockUser
) -> None:
    """Test that input_boolean context works."""
    assert await async_setup_component(
        menuai, "input_boolean", {"input_boolean": {"ac": {CONF_INITIAL: True}}}
    )

    state = menuai.states.get("input_boolean.ac")
    assert state is not None

    await menuai.services.async_call(
        "input_boolean",
        "turn_off",
        {"entity_id": state.entity_id},
        True,
        Context(user_id=menuai_admin_user.id),
    )

    state2 = menuai.states.get("input_boolean.ac")
    assert state2 is not None
    assert state.state != state2.state
    assert state2.context.user_id == menuai_admin_user.id


async def test_reload(
    menuai: menuai, entity_registry: er.EntityRegistry, menuai_admin_user: MockUser
) -> None:
    """Test reload service."""
    count_start = len(menuai.states.async_entity_ids())

    _LOGGER.debug("ENTITIES @ start: %s", menuai.states.async_entity_ids())

    assert await async_setup_component(
        menuai,
        DOMAIN,
        {
            DOMAIN: {
                "test_1": None,
                "test_2": {"name": "Hello World", "icon": "mdi:work", "initial": True},
            }
        },
    )

    _LOGGER.debug("ENTITIES: %s", menuai.states.async_entity_ids())

    assert count_start + 2 == len(menuai.states.async_entity_ids())

    state_1 = menuai.states.get("input_boolean.test_1")
    state_2 = menuai.states.get("input_boolean.test_2")
    state_3 = menuai.states.get("input_boolean.test_3")

    assert state_1 is not None
    assert state_2 is not None
    assert state_3 is None
    assert state_2.state == STATE_ON

    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, "test_1") is not None
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, "test_2") is not None
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, "test_3") is None

    with patch(
        "menuai.config.load_yaml_config_file",
        autospec=True,
        return_value={
            DOMAIN: {
                "test_2": {
                    "name": "Hello World reloaded",
                    "icon": "mdi:work_reloaded",
                    "initial": False,
                },
                "test_3": None,
            }
        },
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            blocking=True,
            context=Context(user_id=menuai_admin_user.id),
        )

    assert count_start + 2 == len(menuai.states.async_entity_ids())

    state_1 = menuai.states.get("input_boolean.test_1")
    state_2 = menuai.states.get("input_boolean.test_2")
    state_3 = menuai.states.get("input_boolean.test_3")

    assert state_1 is None
    assert state_2 is not None
    assert state_3 is not None

    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, "test_1") is None
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, "test_2") is not None
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, "test_3") is not None

    assert state_2.state == STATE_ON  # reload is not supposed to change entity state
    assert state_2.attributes.get(ATTR_FRIENDLY_NAME) == "Hello World reloaded"
    assert state_2.attributes.get(ATTR_ICON) == "mdi:work_reloaded"


async def test_load_from_storage(menuai: menuai, storage_setup) -> None:
    """Test set up from storage."""
    assert await storage_setup()
    state = menuai.states.get(f"{DOMAIN}.from_storage")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "from storage"
    assert state.attributes.get(ATTR_EDITABLE)


async def test_editable_state_attribute(menuai: menuai, storage_setup) -> None:
    """Test editable attribute."""
    assert await storage_setup(config={DOMAIN: {"from_yaml": None}})

    state = menuai.states.get(f"{DOMAIN}.from_storage")
    assert state.state == STATE_OFF
    assert state.attributes.get(ATTR_FRIENDLY_NAME) == "from storage"
    assert state.attributes.get(ATTR_EDITABLE)

    state = menuai.states.get(f"{DOMAIN}.from_yaml")
    assert state.state == STATE_OFF
    assert not state.attributes.get(ATTR_EDITABLE)


async def test_ws_list(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, storage_setup
) -> None:
    """Test listing via WS."""
    assert await storage_setup(config={DOMAIN: {"from_yaml": None}})

    client = await menuai_ws_client(menuai)

    await client.send_json({"id": 6, "type": f"{DOMAIN}/list"})
    resp = await client.receive_json()
    assert resp["success"]

    storage_ent = "from_storage"
    yaml_ent = "from_yaml"
    result = {item["id"]: item for item in resp["result"]}

    assert len(result) == 1
    assert storage_ent in result
    assert yaml_ent not in result
    assert result[storage_ent][ATTR_NAME] == "from storage"


async def test_ws_delete(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    menuai_ws_client: WebSocketGenerator,
    storage_setup,
) -> None:
    """Test WS delete cleans up entity registry."""
    assert await storage_setup()

    input_id = "from_storage"
    input_entity_id = f"{DOMAIN}.{input_id}"

    state = menuai.states.get(input_entity_id)
    assert state is not None
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, input_id) is not None

    client = await menuai_ws_client(menuai)

    await client.send_json(
        {"id": 6, "type": f"{DOMAIN}/delete", f"{DOMAIN}_id": f"{input_id}"}
    )
    resp = await client.receive_json()
    assert resp["success"]

    state = menuai.states.get(input_entity_id)
    assert state is None
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, input_id) is None


async def test_ws_update(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    menuai_ws_client: WebSocketGenerator,
    storage_setup,
) -> None:
    """Test update WS."""

    settings = {
        "name": "from storage",
    }
    items = [{"id": "from_storage"} | settings]
    assert await storage_setup(items)

    input_id = "from_storage"
    input_entity_id = f"{DOMAIN}.{input_id}"

    state = menuai.states.get(input_entity_id)
    assert state is not None
    assert state.state
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, input_id) is not None

    client = await menuai_ws_client(menuai)

    updated_settings = settings | {"name": "new_name", "icon": "mdi:blah"}
    await client.send_json(
        {
            "id": 6,
            "type": f"{DOMAIN}/update",
            f"{DOMAIN}_id": f"{input_id}",
            **updated_settings,
        }
    )
    resp = await client.receive_json()
    assert resp["success"]
    assert resp["result"] == {"id": "from_storage"} | updated_settings

    state = menuai.states.get(input_entity_id)
    assert state.attributes["icon"] == "mdi:blah"
    assert state.attributes["friendly_name"] == "new_name"

    updated_settings = settings | {"name": "new_name_2"}
    await client.send_json(
        {
            "id": 7,
            "type": f"{DOMAIN}/update",
            f"{DOMAIN}_id": f"{input_id}",
            **updated_settings,
        }
    )
    resp = await client.receive_json()
    assert resp["success"]
    assert resp["result"] == {"id": "from_storage"} | updated_settings

    state = menuai.states.get(input_entity_id)
    assert "icon" not in state.attributes
    assert state.attributes["friendly_name"] == "new_name_2"


async def test_ws_create(
    menuai: menuai,
    entity_registry: er.EntityRegistry,
    menuai_ws_client: WebSocketGenerator,
    storage_setup,
) -> None:
    """Test create WS."""
    assert await storage_setup(items=[])

    input_id = "new_input"
    input_entity_id = f"{DOMAIN}.{input_id}"

    state = menuai.states.get(input_entity_id)
    assert state is None
    assert entity_registry.async_get_entity_id(DOMAIN, DOMAIN, input_id) is None

    client = await menuai_ws_client(menuai)

    await client.send_json(
        {
            "id": 6,
            "type": f"{DOMAIN}/create",
            "name": "New Input",
        }
    )
    resp = await client.receive_json()
    assert resp["success"]

    state = menuai.states.get(input_entity_id)
    assert state.state


async def test_setup_no_config(menuai: menuai, menuai_admin_user: MockUser) -> None:
    """Test component setup with no config."""
    count_start = len(menuai.states.async_entity_ids())
    assert await async_setup_component(menuai, DOMAIN, {})

    with patch(
        "menuai.config.load_yaml_config_file", autospec=True, return_value={}
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            blocking=True,
            context=Context(user_id=menuai_admin_user.id),
        )

    assert count_start == len(menuai.states.async_entity_ids())
