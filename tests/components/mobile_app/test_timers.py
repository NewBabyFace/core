"""Test mobile app timers."""

from unittest.mock import patch

import pytest

from menuai.components.mobile_app import DATA_DEVICES, DOMAIN
from menuai.core import menuai
from menuai.helpers import intent as intent_helper


@pytest.mark.parametrize(
    ("intent_args", "message"),
    [
        (
            {},
            "0:02:00 timer finished",
        ),
        (
            {"name": {"value": "pizza"}},
            "pizza finished",
        ),
    ],
)
async def test_timer_events(
    menuai: menuai, push_registration, intent_args: dict, message: str
) -> None:
    """Test for timer events."""
    webhook_id = push_registration["webhook_id"]
    device_id = menuai.data[DOMAIN][DATA_DEVICES][webhook_id].id

    await intent_helper.async_handle(
        menuai,
        "test",
        intent_helper.INTENT_START_TIMER,
        {
            "minutes": {"value": 2},
        }
        | intent_args,
        device_id=device_id,
    )

    with patch(
        "menuai.components.mobile_app.notify.MobileAppNotificationService.async_send_message"
    ) as mock_send_message:
        await intent_helper.async_handle(
            menuai,
            "test",
            intent_helper.INTENT_DECREASE_TIMER,
            {
                "minutes": {"value": 2},
            },
            device_id=device_id,
        )
        await menuai.async_block_till_done()

    assert mock_send_message.mock_calls[0][2] == {
        "target": [webhook_id],
        "message": message,
        "data": {
            "channel": "Timers",
            "group": "timers",
            "importance": "high",
            "ttl": 0,
            "priority": "high",
            "push": {
                "interruption-level": "time-sensitive",
            },
        },
    }
