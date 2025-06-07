"""The tests for Mobile App device actions."""

from menuai.components import automation, device_automation
from menuai.components.mobile_app import DATA_DEVICES, DOMAIN, util
from menuai.core import menuai
from menuai.setup import async_setup_component

from tests.common import async_get_device_automations, patch


async def test_get_actions(menuai: menuai, push_registration) -> None:
    """Test we get the expected actions from a mobile_app."""
    webhook_id = push_registration["webhook_id"]
    device_id = menuai.data[DOMAIN][DATA_DEVICES][webhook_id].id

    assert await async_get_device_automations(
        menuai, device_automation.DeviceAutomationType.ACTION, device_id
    ) == [{"domain": DOMAIN, "device_id": device_id, "metadata": {}, "type": "notify"}]

    capabilitites = await device_automation._async_get_device_automation_capabilities(
        menuai,
        device_automation.DeviceAutomationType.ACTION,
        {"domain": DOMAIN, "device_id": device_id, "type": "notify"},
    )
    assert "extra_fields" in capabilitites


async def test_action(menuai: menuai, push_registration) -> None:
    """Test for turn_on and turn_off actions."""
    webhook_id = push_registration["webhook_id"]

    assert await async_setup_component(
        menuai,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "platform": "event",
                        "event_type": "test_notify",
                    },
                    "action": [
                        {"variables": {"name": "Paulus"}},
                        {
                            "domain": DOMAIN,
                            "device_id": menuai.data[DOMAIN]["devices"][webhook_id].id,
                            "type": "notify",
                            "message": "Hello {{ name }}",
                        },
                    ],
                },
            ]
        },
    )

    service_name = util.get_notify_service(menuai, webhook_id)

    # Make sure it was actually registered
    assert menuai.services.has_service("notify", service_name)

    with patch(
        "menuai.components.mobile_app.notify.MobileAppNotificationService.async_send_message"
    ) as mock_send_message:
        menuai.bus.async_fire("test_notify")
        await menuai.async_block_till_done()
        assert len(mock_send_message.mock_calls) == 1

    assert mock_send_message.mock_calls[0][2] == {
        "target": [webhook_id],
        "message": "Hello Paulus",
        "data": None,
    }
