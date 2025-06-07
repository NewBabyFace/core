"""Test Shopping List intents."""

from menuai.core import menuai
from menuai.helpers import intent


async def test_complete_item_intent(menuai: menuai, sl_setup) -> None:
    """Test complete item."""
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "soda"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "beer"}}
    )
    await intent.async_handle(
        menuai, "test", "menuaiShoppingListAddItem", {"item": {"value": "wine"}}
    )

    response = await intent.async_handle(
        menuai, "test", "menuaiShoppingListCompleteItem", {"item": {"value": "beer"}}
    )

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    completed_items = response.speech_slots.get("completed_items")
    assert len(completed_items) == 2
    assert completed_items[0]["name"] == "beer"
    assert menuai.data["shopping_list"].items[1]["complete"]
    assert menuai.data["shopping_list"].items[2]["complete"]

    # Complete again
    response = await intent.async_handle(
        menuai, "test", "menuaiShoppingListCompleteItem", {"item": {"value": "beer"}}
    )

    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert response.speech_slots.get("completed_items") == []
    assert menuai.data["shopping_list"].items[1]["complete"]
    assert menuai.data["shopping_list"].items[2]["complete"]


async def test_complete_item_intent_not_found(menuai: menuai, sl_setup) -> None:
    """Test completing a missing item."""
    response = await intent.async_handle(
        menuai, "test", "menuaiShoppingListCompleteItem", {"item": {"value": "beer"}}
    )
    assert response.response_type == intent.IntentResponseType.ACTION_DONE
    assert response.speech_slots.get("completed_items") == []


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


async def test_recent_items_intent_no_items(menuai: menuai, sl_setup) -> None:
    """Test recent items."""
    response = await intent.async_handle(menuai, "test", "menuaiShoppingListLastItems")

    assert (
        response.speech["plain"]["speech"] == "There are no items on your shopping list"
    )
