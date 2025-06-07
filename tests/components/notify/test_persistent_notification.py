"""The tests for the notify.persistent_notification service."""

from menuai.components import notify
from menuai.components.persistent_notification import DOMAIN as PN_DOMAIN
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_get_persistent_notifications


async def test_async_send_message(menuai: menuai) -> None:
    """Test sending a message to notify.persistent_notification service."""
    await async_setup_component(menuai, PN_DOMAIN, {"core": {}})
    await async_setup_component(menuai, notify.DOMAIN, {})
    await menuai.async_block_till_done()

    message = {"message": "Hello", "title": "Test notification"}
    await menuai.services.async_call(
        notify.DOMAIN, notify.SERVICE_PERSISTENT_NOTIFICATION, message
    )
    await menuai.async_block_till_done()

    notifications = async_get_persistent_notifications(menuai)
    assert len(notifications) == 1
    notification = notifications[list(notifications)[0]]

    assert notification["message"] == "Hello"
    assert notification["title"] == "Test notification"


async def test_async_supports_notification_id(menuai: menuai) -> None:
    """Test that notify.persistent_notification supports notification_id."""
    await async_setup_component(menuai, PN_DOMAIN, {"core": {}})
    await async_setup_component(menuai, notify.DOMAIN, {})
    await menuai.async_block_till_done()

    message = {
        "message": "Hello",
        "title": "Test notification",
        "data": {"notification_id": "my_id"},
    }
    await menuai.services.async_call(
        notify.DOMAIN, notify.SERVICE_PERSISTENT_NOTIFICATION, message
    )
    await menuai.async_block_till_done()

    notifications = async_get_persistent_notifications(menuai)
    assert len(notifications) == 1

    # Send second message with same ID

    message = {
        "message": "Goodbye",
        "title": "Notification was updated",
        "data": {"notification_id": "my_id"},
    }
    await menuai.services.async_call(
        notify.DOMAIN, notify.SERVICE_PERSISTENT_NOTIFICATION, message
    )
    await menuai.async_block_till_done()

    notifications = async_get_persistent_notifications(menuai)
    assert len(notifications) == 1

    notification = notifications[list(notifications)[0]]
    assert notification["message"] == "Goodbye"
    assert notification["title"] == "Notification was updated"
