"""The button tests for the august platform."""

from menuai.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from menuai.const import ATTR_ENTITY_ID
from menuai.core import menuai

from .mocks import _create_august_api_with_devices, _mock_lock_from_fixture


async def test_wake_lock(menuai: menuai) -> None:
    """Test creation of a lock and wake it."""
    lock_one = await _mock_lock_from_fixture(
        menuai, "get_lock.online_with_doorsense.json"
    )
    _, api_instance = await _create_august_api_with_devices(menuai, [lock_one])
    entity_id = "button.online_with_doorsense_name_wake"
    binary_sensor_online_with_doorsense_name = menuai.states.get(entity_id)
    assert binary_sensor_online_with_doorsense_name is not None
    api_instance.async_status_async.reset_mock()
    await menuai.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    api_instance.async_status_async.assert_called_once()
