"""Test shopping list component."""

from http import HTTPStatus

import pytest

from menuai.components.shopping_list import NoMatchingShoppingListItem
from menuai.components.shopping_list.const import (
    ATTR_REVERSE,
    DOMAIN,
    EVENT_SHOPPING_LIST_UPDATED,
    SERVICE_ADD_ITEM,
    SERVICE_CLEAR_COMPLETED_ITEMS,
    SERVICE_COMPLETE_ITEM,
    SERVICE_REMOVE_ITEM,
    SERVICE_SORT,
)
from menuai.components.websocket_api import (
    ERR_INVALID_FORMAT,
    ERR_NOT_FOUND,
    TYPE_RESULT,
)
from menuai.const import ATTR_NAME
from menuai.core import menuai
from menuai.helpers import intent

from tests.common import async_capture_events
from tests.typing import ClientSessionGenerator, WebSocketGenerator


async def test_add_item(menuai: menuai, sl_setup) -> None:
    """Test adding an item intent."""

    response = await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": " beer "}}
    )
    assert len(menuai.data[DOMAIN].items) == 1
    assert menuai.data[DOMAIN].items[0]["name"] == "beer"  # name was trimmed

    # Response text is now handled by default conversation agent
    assert response.response_type == intent.IntentResponseType.ACTION_DONE


async def test_remove_item(menuai: menuai, sl_setup) -> None:
    """Test removiung list items."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "cheese"}}
    )

    assert len(menuai.data[DOMAIN].items) == 2

    # Remove a single item
    item_id = menuai.data[DOMAIN].items[0]["id"]
    await menuai.data[DOMAIN].async_remove(item_id)

    assert len(menuai.data[DOMAIN].items) == 1

    item = menuai.data[DOMAIN].items[0]
    assert item["name"] == "cheese"

    # Trying to remove the same item twice should fail
    with pytest.raises(NoMatchingShoppingListItem):
        await menuai.data[DOMAIN].async_remove(item_id)


async def test_update_list(menuai: menuai, sl_setup) -> None:
    """Test updating all list items."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "cheese"}}
    )

    # Update a single attribute, other attributes shouldn't change
    await menuai.data[DOMAIN].async_update_list({"complete": True})

    beer = menuai.data[DOMAIN].items[0]
    assert beer["name"] == "beer"
    assert beer["complete"] is True

    cheese = menuai.data[DOMAIN].items[1]
    assert cheese["name"] == "cheese"
    assert cheese["complete"] is True

    # Update multiple attributes
    await menuai.data[DOMAIN].async_update_list({"name": "dupe", "complete": False})

    beer = menuai.data[DOMAIN].items[0]
    assert beer["name"] == "dupe"
    assert beer["complete"] is False

    cheese = menuai.data[DOMAIN].items[1]
    assert cheese["name"] == "dupe"
    assert cheese["complete"] is False


async def test_clear_completed_items(menuai: menuai, sl_setup) -> None:
    """Test clear completed list items."""
    await intent.async_handle(
        menuai,
        "test",
        "menuaiShoppingListAddItem",
        {"item": {"value": "beer"}},
    )

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "cheese"}}
    )

    assert len(menuai.data[DOMAIN].items) == 2

    # Update a single attribute, other attributes shouldn't change
    await menuai.data[DOMAIN].async_update_list({"complete": True})

    await menuai.data[DOMAIN].async_clear_completed()

    assert len(menuai.data[DOMAIN].items) == 0


async def test_recent_items_intent(menuai: menuai, sl_setup) -> None:
    """Test recent items."""

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "soda"}}
    )

    response = await intent.async_handle(menuai, "test", "menuaiShoppingListLastItems")

    assert (
        response.speech["plain"]["speech"]
        == "These are the top 3 items on your shopping list: soda, wine, beer"
    )


async def test_deprecated_api_get_all(
    menuai: menuai, menuai_client: ClientSessionGenerator, sl_setup
) -> None:
    """Test the API."""

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )

    client = await menuai_client()
    resp = await client.get("/api/shopping_list")

    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "beer"
    assert not data[0]["complete"]
    assert data[1]["name"] == "wine"
    assert not data[1]["complete"]


async def test_ws_get_items(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test get shopping_list items websocket command."""

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )

    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)

    await client.send_json({"id": 5, "type": "shopping_list/items"})
    msg = await client.receive_json()
    assert msg["success"] is True
    assert len(events) == 0

    assert msg["id"] == 5
    assert msg["type"] == TYPE_RESULT
    assert msg["success"]
    data = msg["result"]
    assert len(data) == 2
    assert data[0]["name"] == "beer"
    assert not data[0]["complete"]
    assert data[1]["name"] == "wine"
    assert not data[1]["complete"]


async def test_deprecated_api_update(
    menuai: menuai, menuai_client: ClientSessionGenerator, sl_setup
) -> None:
    """Test the API."""

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )

    beer_id = menuai.data["shopping_list"].items[0]["id"]
    wine_id = menuai.data["shopping_list"].items[1]["id"]

    client = await menuai_client()
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    resp = await client.post(
        f"/api/shopping_list/item/{beer_id}", json={"name": "soda"}
    )

    assert resp.status == HTTPStatus.OK
    assert len(events) == 1
    data = await resp.json()
    assert data == {"id": beer_id, "name": "soda", "complete": False}

    resp = await client.post(
        f"/api/shopping_list/item/{wine_id}", json={"complete": True}
    )

    assert resp.status == HTTPStatus.OK
    assert len(events) == 2
    data = await resp.json()
    assert data == {"id": wine_id, "name": "wine", "complete": True}

    beer, wine = menuai.data["shopping_list"].items
    assert beer == {"id": beer_id, "name": "soda", "complete": False}
    assert wine == {"id": wine_id, "name": "wine", "complete": True}


async def test_ws_update_item(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test update shopping_list item websocket command."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )

    beer_id = menuai.data["shopping_list"].items[0]["id"]
    wine_id = menuai.data["shopping_list"].items[1]["id"]
    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json(
        {
            "id": 5,
            "type": "shopping_list/items/update",
            "item_id": beer_id,
            "name": "soda",
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    data = msg["result"]
    assert data == {"id": beer_id, "name": "soda", "complete": False}
    assert len(events) == 1

    await client.send_json(
        {
            "id": 6,
            "type": "shopping_list/items/update",
            "item_id": wine_id,
            "complete": True,
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    data = msg["result"]
    assert data == {"id": wine_id, "name": "wine", "complete": True}
    assert len(events) == 2

    beer, wine = menuai.data["shopping_list"].items
    assert beer == {"id": beer_id, "name": "soda", "complete": False}
    assert wine == {"id": wine_id, "name": "wine", "complete": True}


async def test_api_update_fails(
    menuai: menuai, menuai_client: ClientSessionGenerator, sl_setup
) -> None:
    """Test the API."""

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )

    client = await menuai_client()
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    resp = await client.post("/api/shopping_list/non_existing", json={"name": "soda"})

    assert resp.status == HTTPStatus.NOT_FOUND
    assert len(events) == 0

    beer_id = menuai.data["shopping_list"].items[0]["id"]
    resp = await client.post(f"/api/shopping_list/item/{beer_id}", json={"name": 123})

    assert resp.status == HTTPStatus.BAD_REQUEST


async def test_ws_update_item_fail(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test failure of update shopping_list item websocket command."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json(
        {
            "id": 5,
            "type": "shopping_list/items/update",
            "item_id": "non_existing",
            "name": "soda",
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is False
    data = msg["error"]
    assert data == {"code": "item_not_found", "message": "Item not found"}
    assert len(events) == 0

    await client.send_json({"id": 6, "type": "shopping_list/items/update", "name": 123})
    msg = await client.receive_json()
    assert msg["success"] is False
    assert len(events) == 0


async def test_deprecated_api_clear_completed(
    menuai: menuai, menuai_client: ClientSessionGenerator, sl_setup
) -> None:
    """Test the API."""

    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )

    beer_id = menuai.data["shopping_list"].items[0]["id"]
    wine_id = menuai.data["shopping_list"].items[1]["id"]

    client = await menuai_client()
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)

    # Mark beer as completed
    resp = await client.post(
        f"/api/shopping_list/item/{beer_id}", json={"complete": True}
    )
    assert resp.status == HTTPStatus.OK
    assert len(events) == 1

    resp = await client.post("/api/shopping_list/clear_completed")
    assert resp.status == HTTPStatus.OK
    assert len(events) == 2

    items = menuai.data["shopping_list"].items
    assert len(items) == 1

    assert items[0] == {"id": wine_id, "name": "wine", "complete": False}


async def test_ws_clear_items(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test clearing shopping_list items websocket command."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )
    beer_id = menuai.data["shopping_list"].items[0]["id"]
    wine_id = menuai.data["shopping_list"].items[1]["id"]
    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json(
        {
            "id": 5,
            "type": "shopping_list/items/update",
            "item_id": beer_id,
            "complete": True,
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    assert len(events) == 1

    await client.send_json({"id": 6, "type": "shopping_list/items/clear"})
    msg = await client.receive_json()
    assert msg["success"] is True
    items = menuai.data["shopping_list"].items
    assert len(items) == 1
    assert items[0] == {"id": wine_id, "name": "wine", "complete": False}
    assert len(events) == 2


async def test_deprecated_api_create(
    menuai: menuai, menuai_client: ClientSessionGenerator, sl_setup
) -> None:
    """Test the API."""

    client = await menuai_client()
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    resp = await client.post("/api/shopping_list/item", json={"name": "soda"})

    assert resp.status == HTTPStatus.OK
    data = await resp.json()
    assert data["name"] == "soda"
    assert data["complete"] is False
    assert len(events) == 1

    items = menuai.data["shopping_list"].items
    assert len(items) == 1
    assert items[0]["name"] == "soda"
    assert items[0]["complete"] is False


async def test_deprecated_api_create_fail(
    menuai: menuai, menuai_client: ClientSessionGenerator, sl_setup
) -> None:
    """Test the API."""

    client = await menuai_client()
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    resp = await client.post("/api/shopping_list/item", json={"name": 1234})

    assert resp.status == HTTPStatus.BAD_REQUEST
    assert len(menuai.data["shopping_list"].items) == 0
    assert len(events) == 0


async def test_ws_add_item(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test adding shopping_list item websocket command."""
    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json({"id": 5, "type": "shopping_list/items/add", "name": "soda"})
    msg = await client.receive_json()
    assert msg["success"] is True
    data = msg["result"]
    assert data["name"] == "soda"
    assert data["complete"] is False
    assert len(events) == 1

    items = menuai.data["shopping_list"].items
    assert len(items) == 1
    assert items[0]["name"] == "soda"
    assert items[0]["complete"] is False


async def test_ws_add_item_fail(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test adding shopping_list item failure websocket command."""
    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json({"id": 5, "type": "shopping_list/items/add", "name": 123})
    msg = await client.receive_json()
    assert msg["success"] is False
    assert len(events) == 0
    assert len(menuai.data["shopping_list"].items) == 0


async def test_ws_remove_item(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test removing shopping_list item websocket command."""
    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json({"id": 5, "type": "shopping_list/items/add", "name": "soda"})
    msg = await client.receive_json()
    first_item_id = msg["result"]["id"]
    await client.send_json(
        {"id": 6, "type": "shopping_list/items/add", "name": "cheese"}
    )
    msg = await client.receive_json()
    assert len(events) == 2

    items = menuai.data["shopping_list"].items
    assert len(items) == 2

    await client.send_json(
        {"id": 7, "type": "shopping_list/items/remove", "item_id": first_item_id}
    )
    msg = await client.receive_json()
    assert len(events) == 3
    assert msg["success"] is True

    items = menuai.data["shopping_list"].items
    assert len(items) == 1
    assert items[0]["name"] == "cheese"


async def test_ws_remove_item_fail(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test removing shopping_list item failure websocket command."""
    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json({"id": 5, "type": "shopping_list/items/add", "name": "soda"})
    msg = await client.receive_json()
    await client.send_json({"id": 6, "type": "shopping_list/items/remove"})
    msg = await client.receive_json()
    assert msg["success"] is False
    assert len(events) == 1
    assert len(menuai.data["shopping_list"].items) == 1


async def test_ws_reorder_items(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test reordering shopping_list items websocket command."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "apple"}}
    )

    beer_id = menuai.data["shopping_list"].items[0]["id"]
    wine_id = menuai.data["shopping_list"].items[1]["id"]
    apple_id = menuai.data["shopping_list"].items[2]["id"]

    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await client.send_json(
        {
            "id": 6,
            "type": "shopping_list/items/reorder",
            "item_ids": [wine_id, apple_id, beer_id],
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    assert len(events) == 1
    assert menuai.data["shopping_list"].items[0] == {
        "id": wine_id,
        "name": "wine",
        "complete": False,
    }
    assert menuai.data["shopping_list"].items[1] == {
        "id": apple_id,
        "name": "apple",
        "complete": False,
    }
    assert menuai.data["shopping_list"].items[2] == {
        "id": beer_id,
        "name": "beer",
        "complete": False,
    }

    # Mark wine as completed.
    await client.send_json(
        {
            "id": 7,
            "type": "shopping_list/items/update",
            "item_id": wine_id,
            "complete": True,
        }
    )
    _ = await client.receive_json()
    assert len(events) == 2

    await client.send_json(
        {
            "id": 8,
            "type": "shopping_list/items/reorder",
            "item_ids": [apple_id, beer_id],
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is True
    assert len(events) == 3
    assert menuai.data["shopping_list"].items[0] == {
        "id": apple_id,
        "name": "apple",
        "complete": False,
    }
    assert menuai.data["shopping_list"].items[1] == {
        "id": beer_id,
        "name": "beer",
        "complete": False,
    }
    assert menuai.data["shopping_list"].items[2] == {
        "id": wine_id,
        "name": "wine",
        "complete": True,
    }


async def test_ws_reorder_items_failure(
    menuai: menuai, menuai_ws_client: WebSocketGenerator, sl_setup
) -> None:
    """Test reordering shopping_list items websocket command."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "apple"}}
    )

    beer_id = menuai.data["shopping_list"].items[0]["id"]
    wine_id = menuai.data["shopping_list"].items[1]["id"]
    apple_id = menuai.data["shopping_list"].items[2]["id"]

    client = await menuai_ws_client(menuai)
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)

    # Testing sending bad item id.
    await client.send_json(
        {
            "id": 8,
            "type": "shopping_list/items/reorder",
            "item_ids": [wine_id, apple_id, beer_id, "BAD_ID"],
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is False
    assert msg["error"]["code"] == ERR_NOT_FOUND
    assert len(events) == 0

    # Testing not sending all unchecked item ids.
    await client.send_json(
        {
            "id": 9,
            "type": "shopping_list/items/reorder",
            "item_ids": [wine_id, apple_id],
        }
    )
    msg = await client.receive_json()
    assert msg["success"] is False
    assert msg["error"]["code"] == ERR_INVALID_FORMAT
    assert len(events) == 0


async def test_add_item_service(menuai: menuai, sl_setup) -> None:
    """Test adding shopping_list item service."""
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_ADD_ITEM,
        {ATTR_NAME: "beer"},
        blocking=True,
    )
    assert len(menuai.data[DOMAIN].items) == 1
    assert len(events) == 1


async def test_remove_item_service(menuai: menuai, sl_setup) -> None:
    """Test removing shopping_list item service."""
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_ADD_ITEM,
        {ATTR_NAME: "beer"},
        blocking=True,
    )
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_ADD_ITEM,
        {ATTR_NAME: "cheese"},
        blocking=True,
    )
    assert len(menuai.data[DOMAIN].items) == 2
    assert len(events) == 2

    await menuai.services.async_call(
        DOMAIN,
        SERVICE_REMOVE_ITEM,
        {ATTR_NAME: "beer"},
        blocking=True,
    )
    assert len(menuai.data[DOMAIN].items) == 1
    assert menuai.data[DOMAIN].items[0]["name"] == "cheese"
    assert len(events) == 3


async def test_clear_completed_items_service(menuai: menuai, sl_setup) -> None:
    """Test clearing completed shopping_list items service."""
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_ADD_ITEM,
        {ATTR_NAME: "beer"},
        blocking=True,
    )
    assert len(menuai.data[DOMAIN].items) == 1
    assert len(events) == 1

    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_COMPLETE_ITEM,
        {ATTR_NAME: "beer"},
        blocking=True,
    )
    assert len(menuai.data[DOMAIN].items) == 1
    assert len(events) == 1

    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_CLEAR_COMPLETED_ITEMS,
        {},
        blocking=True,
    )
    assert len(menuai.data[DOMAIN].items) == 0
    assert len(events) == 1


async def test_sort_list_service(menuai: menuai, sl_setup) -> None:
    """Test sort_all service."""

    for name in ("zzz", "ddd", "aaa"):
        await menuai.services.async_call(
            DOMAIN,
            SERVICE_ADD_ITEM,
            {ATTR_NAME: name},
            blocking=True,
        )

    # sort ascending
    events = async_capture_events(menuai, EVENT_SHOPPING_LIST_UPDATED)
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SORT,
        {ATTR_REVERSE: False},
        blocking=True,
    )

    assert menuai.data[DOMAIN].items[0][ATTR_NAME] == "aaa"
    assert menuai.data[DOMAIN].items[1][ATTR_NAME] == "ddd"
    assert menuai.data[DOMAIN].items[2][ATTR_NAME] == "zzz"
    assert len(events) == 1

    # sort descending
    await menuai.services.async_call(
        DOMAIN,
        SERVICE_SORT,
        {ATTR_REVERSE: True},
        blocking=True,
    )

    assert menuai.data[DOMAIN].items[0][ATTR_NAME] == "zzz"
    assert menuai.data[DOMAIN].items[1][ATTR_NAME] == "ddd"
    assert menuai.data[DOMAIN].items[2][ATTR_NAME] == "aaa"
    assert len(events) == 2
