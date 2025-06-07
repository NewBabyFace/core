"""The tests for the person component."""

from typing import Any
from unittest.mock import patch

import pytest

from menuai.components import person
from menuai.components.device_tracker import ATTR_SOURCE_TYPE, SourceType
from menuai.components.person import (
    ATTR_DEVICE_TRACKERS,
    ATTR_SOURCE,
    ATTR_USER_ID,
    DOMAIN,
)
from menuai.const import (
    ATTR_ENTITY_PICTURE,
    ATTR_GPS_ACCURACY,
    ATTR_ID,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    EVENT_menuai_START,
    SERVICE_RELOAD,
    STATE_UNKNOWN,
)
from menuai.core import Context, CoreState, menuai, State
from menuai.helpers import entity_registry as er
from menuai.setup import async_setup_component

from .conftest import DEVICE_TRACKER, DEVICE_TRACKER_2

from tests.common import MockUser, mock_component, mock_restore_cache
from tests.typing import WebSocketGenerator


async def test_minimal_setup(menuai: menuai) -> None:
    """Test minimal config with only name."""
    config = {DOMAIN: {"id": "1234", "name": "test person"}}
    assert await async_setup_component(menuai, DOMAIN, config)

    state = menuai.states.get("person.test_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) is None
    assert state.attributes.get(ATTR_ENTITY_PICTURE) is None


async def test_setup_no_id(menuai: menuai) -> None:
    """Test config with no id."""
    config = {DOMAIN: {"name": "test user"}}
    assert not await async_setup_component(menuai, DOMAIN, config)


async def test_setup_no_name(menuai: menuai) -> None:
    """Test config with no name."""
    config = {DOMAIN: {"id": "1234"}}
    assert not await async_setup_component(menuai, DOMAIN, config)


async def test_setup_user_id(menuai: menuai, menuai_admin_user: MockUser) -> None:
    """Test config with user id."""
    user_id = menuai_admin_user.id
    config = {DOMAIN: {"id": "1234", "name": "test person", "user_id": user_id}}
    assert await async_setup_component(menuai, DOMAIN, config)

    state = menuai.states.get("person.test_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id


async def test_valid_invalid_user_ids(
    menuai: menuai, menuai_admin_user: MockUser
) -> None:
    """Test a person with valid user id and a person with invalid user id ."""
    user_id = menuai_admin_user.id
    config = {
        DOMAIN: [
            {"id": "1234", "name": "test valid user", "user_id": user_id},
            {"id": "5678", "name": "test bad user", "user_id": "bad_user_id"},
        ]
    }
    assert await async_setup_component(menuai, DOMAIN, config)

    state = menuai.states.get("person.test_valid_user")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id
    state = menuai.states.get("person.test_bad_user")
    assert state is None


async def test_setup_tracker(menuai: menuai, menuai_admin_user: MockUser) -> None:
    """Test set up person with one device tracker."""
    menuai.set_state(CoreState.not_running)
    user_id = menuai_admin_user.id
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": DEVICE_TRACKER,
        }
    }
    assert await async_setup_component(menuai, DOMAIN, config)

    state = menuai.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id

    menuai.states.async_set(DEVICE_TRACKER, "home")
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == user_id
    assert state.attributes.get(ATTR_DEVICE_TRACKERS) == [DEVICE_TRACKER]

    menuai.states.async_set(
        DEVICE_TRACKER,
        "not_home",
        {ATTR_LATITUDE: 10.123456, ATTR_LONGITUDE: 11.123456, ATTR_GPS_ACCURACY: 10},
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "not_home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) == 10.123456
    assert state.attributes.get(ATTR_LONGITUDE) == 11.123456
    assert state.attributes.get(ATTR_GPS_ACCURACY) == 10
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == user_id
    assert state.attributes.get(ATTR_DEVICE_TRACKERS) == [DEVICE_TRACKER]


async def test_setup_two_trackers(
    menuai: menuai, menuai_admin_user: MockUser
) -> None:
    """Test set up person with two device trackers."""
    menuai.set_state(CoreState.not_running)
    user_id = menuai_admin_user.id
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": [DEVICE_TRACKER, DEVICE_TRACKER_2],
        }
    }
    assert await async_setup_component(menuai, DOMAIN, config)

    state = menuai.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == user_id

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.states.async_set(DEVICE_TRACKER, "home", {ATTR_SOURCE_TYPE: SourceType.ROUTER})
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_GPS_ACCURACY) is None
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == user_id
    assert state.attributes.get(ATTR_DEVICE_TRACKERS) == [
        DEVICE_TRACKER,
        DEVICE_TRACKER_2,
    ]

    menuai.states.async_set(
        DEVICE_TRACKER_2,
        "not_home",
        {
            ATTR_LATITUDE: 12.123456,
            ATTR_LONGITUDE: 13.123456,
            ATTR_GPS_ACCURACY: 12,
            ATTR_SOURCE_TYPE: SourceType.GPS,
        },
    )
    await menuai.async_block_till_done()
    menuai.states.async_set(
        DEVICE_TRACKER, "not_home", {ATTR_SOURCE_TYPE: SourceType.ROUTER}
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "not_home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) == 12.123456
    assert state.attributes.get(ATTR_LONGITUDE) == 13.123456
    assert state.attributes.get(ATTR_GPS_ACCURACY) == 12
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER_2
    assert state.attributes.get(ATTR_USER_ID) == user_id
    assert state.attributes.get(ATTR_DEVICE_TRACKERS) == [
        DEVICE_TRACKER,
        DEVICE_TRACKER_2,
    ]

    menuai.states.async_set(DEVICE_TRACKER_2, "zone1", {ATTR_SOURCE_TYPE: SourceType.GPS})
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "zone1"
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER_2

    menuai.states.async_set(DEVICE_TRACKER, "home", {ATTR_SOURCE_TYPE: SourceType.ROUTER})
    await menuai.async_block_till_done()
    menuai.states.async_set(DEVICE_TRACKER_2, "zone2", {ATTR_SOURCE_TYPE: SourceType.GPS})
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER


async def test_ignore_unavailable_states(
    menuai: menuai, menuai_admin_user: MockUser
) -> None:
    """Test set up person with two device trackers, one unavailable."""
    menuai.set_state(CoreState.not_running)
    user_id = menuai_admin_user.id
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": [DEVICE_TRACKER, DEVICE_TRACKER_2],
        }
    }
    assert await async_setup_component(menuai, DOMAIN, config)

    state = menuai.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.states.async_set(DEVICE_TRACKER, "home")
    await menuai.async_block_till_done()
    menuai.states.async_set(DEVICE_TRACKER, "unavailable")
    await menuai.async_block_till_done()

    # Unknown, as only 1 device tracker has a state, but we ignore that one
    state = menuai.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN

    menuai.states.async_set(DEVICE_TRACKER_2, "not_home")
    await menuai.async_block_till_done()

    # Take state of tracker 2
    state = menuai.states.get("person.tracked_person")
    assert state.state == "not_home"

    # state 1 is newer but ignored, keep tracker 2 state
    menuai.states.async_set(DEVICE_TRACKER, "unknown")
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "not_home"


async def test_restore_home_state(
    menuai: menuai, menuai_admin_user: MockUser
) -> None:
    """Test that the state is restored for a person on startup."""
    user_id = menuai_admin_user.id
    attrs = {
        ATTR_ID: "1234",
        ATTR_LATITUDE: 10.12346,
        ATTR_LONGITUDE: 11.12346,
        ATTR_SOURCE: DEVICE_TRACKER,
        ATTR_USER_ID: user_id,
    }
    state = State("person.tracked_person", "home", attrs)
    mock_restore_cache(menuai, (state,))
    menuai.set_state(CoreState.not_running)
    mock_component(menuai, "recorder")
    config = {
        DOMAIN: {
            "id": "1234",
            "name": "tracked person",
            "user_id": user_id,
            "device_trackers": DEVICE_TRACKER,
            "picture": "/bla",
        }
    }
    assert await async_setup_component(menuai, DOMAIN, config)

    state = menuai.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) == 10.12346
    assert state.attributes.get(ATTR_LONGITUDE) == 11.12346
    # When restoring state the entity_id of the person will be used as source.
    assert state.attributes.get(ATTR_SOURCE) == "person.tracked_person"
    assert state.attributes.get(ATTR_USER_ID) == user_id
    assert state.attributes.get(ATTR_ENTITY_PICTURE) == "/bla"


async def test_duplicate_ids(menuai: menuai, menuai_admin_user: MockUser) -> None:
    """Test we don't allow duplicate IDs."""
    config = {
        DOMAIN: [
            {"id": "1234", "name": "test user 1"},
            {"id": "1234", "name": "test user 2"},
        ]
    }
    assert await async_setup_component(menuai, DOMAIN, config)

    assert len(menuai.states.async_entity_ids("person")) == 1
    assert menuai.states.get("person.test_user_1") is not None
    assert menuai.states.get("person.test_user_2") is None


async def test_create_person_during_run(menuai: menuai) -> None:
    """Test that person is updated if created while menuai is running."""
    config = {DOMAIN: {}}
    assert await async_setup_component(menuai, DOMAIN, config)
    menuai.states.async_set(DEVICE_TRACKER, "home")
    await menuai.async_block_till_done()

    await person.async_create_person(
        menuai, "tracked person", device_trackers=[DEVICE_TRACKER]
    )
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "home"


async def test_load_person_storage(
    menuai: menuai, menuai_admin_user: MockUser, storage_setup
) -> None:
    """Test set up person from storage."""
    state = menuai.states.get("person.tracked_person")
    assert state.state == STATE_UNKNOWN
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) is None
    assert state.attributes.get(ATTR_USER_ID) == menuai_admin_user.id

    menuai.bus.async_fire(EVENT_menuai_START)
    await menuai.async_block_till_done()
    menuai.states.async_set(DEVICE_TRACKER, "home")
    await menuai.async_block_till_done()

    state = menuai.states.get("person.tracked_person")
    assert state.state == "home"
    assert state.attributes.get(ATTR_ID) == "1234"
    assert state.attributes.get(ATTR_LATITUDE) is None
    assert state.attributes.get(ATTR_LONGITUDE) is None
    assert state.attributes.get(ATTR_SOURCE) == DEVICE_TRACKER
    assert state.attributes.get(ATTR_USER_ID) == menuai_admin_user.id


async def test_load_person_storage_two_nonlinked(
    menuai: menuai, menuai_storage: dict[str, Any]
) -> None:
    """Test loading two users with both not having a user linked."""
    menuai_storage[DOMAIN] = {
        "key": DOMAIN,
        "version": 1,
        "data": {
            "persons": [
                {
                    "id": "1234",
                    "name": "tracked person 1",
                    "user_id": None,
                    "device_trackers": [],
                },
                {
                    "id": "5678",
                    "name": "tracked person 2",
                    "user_id": None,
                    "device_trackers": [],
                },
            ]
        },
    }
    await async_setup_component(menuai, DOMAIN, {})

    assert len(menuai.states.async_entity_ids("person")) == 2
    assert menuai.states.get("person.tracked_person_1") is not None
    assert menuai.states.get("person.tracked_person_2") is not None


async def test_ws_list(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, storage_setup
) -> None:
    """Test listing via WS."""
    manager = menuai.data[DOMAIN][1]

    client = await menuai_ws_client(menuai)

    resp = await client.send_json({"id": 6, "type": "person/list"})
    resp = await client.receive_json()
    assert resp["success"]
    assert resp["result"]["storage"] == manager.async_items()
    assert len(resp["result"]["storage"]) == 1
    assert len(resp["result"]["config"]) == 0


async def test_ws_create(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    storage_setup,
    menuai_read_only_user: MockUser,
) -> None:
    """Test creating via WS."""
    manager = menuai.data[DOMAIN][1]

    client = await menuai_ws_client(menuai)

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/create",
            "name": "Hello",
            "device_trackers": [DEVICE_TRACKER],
            "user_id": menuai_read_only_user.id,
            "picture": "/bla",
        }
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 2

    assert resp["success"]
    assert resp["result"] == persons[1]


async def test_ws_create_requires_admin(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    storage_setup,
    menuai_admin_user: MockUser,
    menuai_read_only_user: MockUser,
) -> None:
    """Test creating via WS requires admin."""
    menuai_admin_user.groups = []
    manager = menuai.data[DOMAIN][1]

    client = await menuai_ws_client(menuai)

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/create",
            "name": "Hello",
            "device_trackers": [DEVICE_TRACKER],
            "user_id": menuai_read_only_user.id,
        }
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 1

    assert not resp["success"]


async def test_ws_update(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, storage_setup
) -> None:
    """Test updating via WS."""
    manager = menuai.data[DOMAIN][1]

    client = await menuai_ws_client(menuai)
    persons = manager.async_items()

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/update",
            "person_id": persons[0]["id"],
            "user_id": persons[0]["user_id"],
        }
    )
    resp = await client.receive_json()

    assert resp["success"]

    resp = await client.send_json(
        {
            "id": 7,
            "type": "person/update",
            "person_id": persons[0]["id"],
            "name": "Updated Name",
            "device_trackers": [DEVICE_TRACKER_2],
            "user_id": None,
            "picture": "/bla",
        }
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 1

    assert resp["success"]
    assert resp["result"] == persons[0]
    assert persons[0]["name"] == "Updated Name"
    assert persons[0]["name"] == "Updated Name"
    assert persons[0]["device_trackers"] == [DEVICE_TRACKER_2]
    assert persons[0]["user_id"] is None
    assert persons[0]["picture"] == "/bla"

    state = menuai.states.get("person.tracked_person")
    assert state.name == "Updated Name"


async def test_ws_update_require_admin(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    storage_setup,
    menuai_admin_user: MockUser,
) -> None:
    """Test updating via WS requires admin."""
    menuai_admin_user.groups = []
    manager = menuai.data[DOMAIN][1]

    client = await menuai_ws_client(menuai)
    original = dict(manager.async_items()[0])

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/update",
            "person_id": original["id"],
            "name": "Updated Name",
            "device_trackers": [DEVICE_TRACKER_2],
            "user_id": None,
        }
    )
    resp = await client.receive_json()
    assert not resp["success"]

    not_updated = dict(manager.async_items()[0])
    assert original == not_updated


async def test_ws_delete(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    entity_registry: er.EntityRegistry,
    storage_setup,
) -> None:
    """Test deleting via WS."""
    manager = menuai.data[DOMAIN][1]

    client = await menuai_ws_client(menuai)
    persons = manager.async_items()

    resp = await client.send_json(
        {"id": 6, "type": "person/delete", "person_id": persons[0]["id"]}
    )
    resp = await client.receive_json()

    persons = manager.async_items()
    assert len(persons) == 0

    assert resp["success"]
    assert len(menuai.states.async_entity_ids("person")) == 0
    assert not entity_registry.async_is_registered("person.tracked_person")


async def test_ws_delete_require_admin(
    menuai: menuai,
    menuai_ws_client: WebSocketGenerator,
    storage_setup,
    menuai_admin_user: MockUser,
) -> None:
    """Test deleting via WS requires admin."""
    menuai_admin_user.groups = []
    manager = menuai.data[DOMAIN][1]

    client = await menuai_ws_client(menuai)

    resp = await client.send_json(
        {
            "id": 6,
            "type": "person/delete",
            "person_id": manager.async_items()[0]["id"],
            "name": "Updated Name",
            "device_trackers": [DEVICE_TRACKER_2],
            "user_id": None,
        }
    )
    resp = await client.receive_json()
    assert not resp["success"]

    persons = manager.async_items()
    assert len(persons) == 1


async def test_create_invalid_user_id(menuai: menuai, storage_collection) -> None:
    """Test we do not allow invalid user ID during creation."""
    with pytest.raises(ValueError):
        await storage_collection.async_create_item(
            {"name": "Hello", "user_id": "non-existing"}
        )


async def test_create_duplicate_user_id(
    menuai: menuai, menuai_admin_user: MockUser, storage_collection
) -> None:
    """Test we do not allow duplicate user ID during creation."""
    await storage_collection.async_create_item(
        {"name": "Hello", "user_id": menuai_admin_user.id}
    )

    with pytest.raises(ValueError):
        await storage_collection.async_create_item(
            {"name": "Hello", "user_id": menuai_admin_user.id}
        )


async def test_update_double_user_id(
    menuai: menuai, menuai_admin_user: MockUser, storage_collection
) -> None:
    """Test we do not allow double user ID during update."""
    await storage_collection.async_create_item(
        {"name": "Hello", "user_id": menuai_admin_user.id}
    )
    person = await storage_collection.async_create_item({"name": "Hello"})

    with pytest.raises(ValueError):
        await storage_collection.async_update_item(
            person["id"], {"user_id": menuai_admin_user.id}
        )


async def test_update_invalid_user_id(menuai: menuai, storage_collection) -> None:
    """Test updating to invalid user ID."""
    person = await storage_collection.async_create_item({"name": "Hello"})

    with pytest.raises(ValueError):
        await storage_collection.async_update_item(
            person["id"], {"user_id": "non-existing"}
        )


async def test_update_person_when_user_removed(
    menuai: menuai, storage_setup, menuai_read_only_user: MockUser
) -> None:
    """Update person when user is removed."""
    storage_collection = menuai.data[DOMAIN][1]

    person = await storage_collection.async_create_item(
        {"name": "Hello", "user_id": menuai_read_only_user.id}
    )

    await menuai.auth.async_remove_user(menuai_read_only_user)
    await menuai.async_block_till_done()

    assert storage_collection.data[person["id"]]["user_id"] is None


async def test_removing_device_tracker(
    menuai: menuai, entity_registry: er.EntityRegistry, storage_setup
) -> None:
    """Test we automatically remove removed device trackers."""
    storage_collection = menuai.data[DOMAIN][1]
    entry = entity_registry.async_get_or_create(
        "device_tracker", "mobile_app", "bla", suggested_object_id="pixel"
    )

    person = await storage_collection.async_create_item(
        {"name": "Hello", "device_trackers": [entry.entity_id]}
    )

    entity_registry.async_remove(entry.entity_id)
    await menuai.async_block_till_done()

    assert storage_collection.data[person["id"]]["device_trackers"] == []


async def test_add_user_device_tracker(
    menuai: menuai, storage_setup, menuai_read_only_user: MockUser
) -> None:
    """Test adding a device tracker to a person tied to a user."""
    storage_collection = menuai.data[DOMAIN][1]
    pers = await storage_collection.async_create_item(
        {
            "name": "Hello",
            "user_id": menuai_read_only_user.id,
            "device_trackers": ["device_tracker.on_create"],
        }
    )

    await person.async_add_user_device_tracker(
        menuai, menuai_read_only_user.id, "device_tracker.added"
    )

    assert storage_collection.data[pers["id"]]["device_trackers"] == [
        "device_tracker.on_create",
        "device_tracker.added",
    ]


async def test_reload(menuai: menuai, menuai_admin_user: MockUser) -> None:
    """Test reloading the YAML config."""
    assert await async_setup_component(
        menuai,
        DOMAIN,
        {
            DOMAIN: [
                {"name": "Person 1", "id": "id-1"},
                {"name": "Person 2", "id": "id-2"},
            ]
        },
    )

    assert len(menuai.states.async_entity_ids()) == 2

    state_1 = menuai.states.get("person.person_1")
    state_2 = menuai.states.get("person.person_2")
    state_3 = menuai.states.get("person.person_3")

    assert state_1 is not None
    assert state_1.name == "Person 1"
    assert state_2 is not None
    assert state_2.name == "Person 2"
    assert state_3 is None

    with patch(
        "menuai.config.load_yaml_config_file",
        autospec=True,
        return_value={
            DOMAIN: [
                {"name": "Person 1-updated", "id": "id-1"},
                {"name": "Person 3", "id": "id-3"},
            ]
        },
    ):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_RELOAD,
            blocking=True,
            context=Context(user_id=menuai_admin_user.id),
        )
        await menuai.async_block_till_done()

    assert len(menuai.states.async_entity_ids()) == 2

    state_1 = menuai.states.get("person.person_1")
    state_2 = menuai.states.get("person.person_2")
    state_3 = menuai.states.get("person.person_3")

    assert state_1 is not None
    assert state_1.name == "Person 1-updated"
    assert state_2 is None
    assert state_3 is not None
    assert state_3.name == "Person 3"


async def test_person_storage_fixing_device_trackers(storage_collection) -> None:
    """Test None device trackers become lists."""
    with patch.object(
        storage_collection.store,
        "async_load",
        return_value={"items": [{"id": "bla", "name": "bla", "device_trackers": None}]},
    ):
        await storage_collection.async_load()

    assert storage_collection.data["bla"]["device_trackers"] == []


async def test_persons_with_entity(menuai: menuai) -> None:
    """Test finding persons with an entity."""
    assert await async_setup_component(
        menuai,
        "person",
        {
            "person": [
                {
                    "id": "abcd",
                    "name": "Paulus",
                    "device_trackers": [
                        "device_tracker.paulus_iphone",
                        "device_tracker.paulus_ipad",
                    ],
                },
                {
                    "id": "efgh",
                    "name": "Anne Therese",
                    "device_trackers": [
                        "device_tracker.at_pixel",
                    ],
                },
            ]
        },
    )

    assert person.persons_with_entity(menuai, "device_tracker.paulus_iphone") == [
        "person.paulus"
    ]


async def test_entities_in_person(menuai: menuai) -> None:
    """Test finding entities tracked by person."""
    assert await async_setup_component(
        menuai,
        "person",
        {
            "person": [
                {
                    "id": "abcd",
                    "name": "Paulus",
                    "device_trackers": [
                        "device_tracker.paulus_iphone",
                        "device_tracker.paulus_ipad",
                    ],
                }
            ]
        },
    )

    assert person.entities_in_person(menuai, "person.paulus") == [
        "device_tracker.paulus_iphone",
        "device_tracker.paulus_ipad",
    ]
